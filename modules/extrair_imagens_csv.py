
import streamlit as st
import requests
import pandas as pd
import re
import os
import zipfile
import concurrent.futures

# ================= UI / THEME =================
st.set_page_config(page_title="EXTRAIR IMAGENS CSV", page_icon="🛍️", layout="centered")

# Basic clean styling (blue professional)
st.markdown("""
    <style>
        .main { background-color: #f9fafb; }
        h1, h2, h3, h4 { color: #111827; font-family: 'Inter', sans-serif; }
        .header-title {
            font-size: 26px; font-weight: 800;
            color: #111827; letter-spacing: 0.5px;
        }
        .brand-chip {
            display:inline-block; padding:6px 12px; border-radius: 10px;
            background: #eaf2ff; color:#1e40af; font-weight:700; margin-right:8px;
        }
        .stButton>button {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border-radius: 10px;
            height: 3em; width: 100%; font-weight: 700;
            border: 1px solid #1d4ed8;
        }
        .stButton>button:hover { background-color: #1d4ed8 !important; }
        .stTextInput>div>div>input, .stPassword>div>div>input, .stSelectbox>div>div>select {
            border-radius: 8px; border: 1px solid #d1d5db;
        }
        .hint { color:#6b7280; font-size: 12px; }
        .card { background:#ffffff; padding:16px; border:1px solid #e5e7eb; border-radius:12px; }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<span class="brand-chip">V2 LABS</span>', unsafe_allow_html=True)
st.title("EXTRAIR IMAGENS CSV")
st.caption("Extrator de links e imagens de produtos por coleção (Shopify Admin API).")
st.divider()

# ================= Core helpers =================
def verificar_permissoes(base_url, headers):
    """Check minimum scopes for Admin API: read_products + read_collections"""
    endpoints = {
        "Produtos": "/products.json?limit=1",
        "Coleções": "/custom_collections.json?limit=1",
    }
    results = {}
    for nome, ep in endpoints.items():
        try:
            r = requests.get(base_url + ep, headers=headers, timeout=20)
            results[nome] = (r.status_code == 200)
        except Exception:
            results[nome] = False
    return all(results.values()), results

def buscar_colecoes(base_url, headers):
    """Fetch all custom + smart collections (paginated)"""
    colecoes = []
    for ctype in ["custom_collections", "smart_collections"]:
        url = f"{base_url}/{ctype}.json?limit=250"
        while True:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code != 200:
                break
            data = r.json().get(ctype, [])
            for c in data:
                colecoes.append({
                    "id": str(c.get("id")),
                    "handle": c.get("handle", ""),
                    "title": c.get("title", "")
                })
            link = r.headers.get("link", "")
            if 'rel="next"' in link:
                page_info = link.split("page_info=")[-1].split(">")[0]
                url = f"{base_url}/{ctype}.json?limit=250&page_info={page_info}"
            else:
                break
    return colecoes

def buscar_produtos(base_url, headers, collection_id):
    """Fetch all products in a collection (paginated)"""
    produtos, page_info = [], None
    while True:
        url = f"{base_url}/collections/{collection_id}/products.json?limit=250"
        if page_info:
            url += f"&page_info={page_info}"
        r = requests.get(url, headers=headers, timeout=60)
        if r.status_code != 200:
            break
        produtos.extend(r.json().get("products", []))
        link = r.headers.get("link", "")
        if 'rel="next"' in link:
            page_info = link.split("page_info=")[-1].split(">")[0]
        else:
            break
    return produtos

def baixar_imagem(url, caminho):
    """Download a single image with basic timeout handling."""
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            with open(caminho, "wb") as f:
                f.write(r.content)
    except Exception:
        pass

# ================= UI Inputs =================
with st.container():
    st.subheader("🔧 Configuração de Acesso")
    colA, colB = st.columns(2)
    with colA:
        shop_name = st.text_input("Nome da Loja (ex: a608d7-cf)", help="Endereço myshopify.com sem o sufixo.")
    with colB:
        api_version = st.text_input("API Version", value="2023-10", help="Versão Admin API (ex: 2023-10).")
    access_token = st.text_input("Access Token (shpat_...)", type="password")
    collection_input = st.text_input("Coleção (ID, handle ou URL)", placeholder="ex: dunk ou https://sualoja.com/collections/dunk")

    st.subheader("⚙️ Opções")
    modo = st.radio(
        "Selecione a ação:",
        ["🔗 Gerar apenas CSV com links", "📦 Baixar imagens e gerar ZIP por produto"],
        index=0,
        help="CSV é mais rápido; ZIP baixa os arquivos para uso offline."
    )
    turbo = st.checkbox("⚡ Ativar modo turbo (downloads paralelos)", value=True) if "📦" in modo else False

start = st.button("▶️ Iniciar Exportação", type="primary", use_container_width=True)

# ================= Execution =================
if start:
    if not shop_name or not access_token or not collection_input:
        st.warning("Preencha **loja**, **token** e **coleção** para continuar.")
        st.stop()

    base_url = f"https://{shop_name}.myshopify.com/admin/api/{api_version}"
    headers = {"X-Shopify-Access-Token": access_token}

    with st.status("Validando permissões de API...", expanded=False) as status:
        ok, detail = verificar_permissoes(base_url, headers)
        if not ok:
            st.error("❌ Token sem permissões suficientes. Ative **read_products** e **read_collections** na sua app.")
            st.write(detail)
            status.update(label="Permissões insuficientes", state="error")
            st.stop()
        status.update(label="Permissões OK", state="complete")

    with st.status("Localizando coleção...", expanded=False) as status:
        colecoes = buscar_colecoes(base_url, headers)
        match = re.search(r'/collections/([^/?#]+)', collection_input or "")
        col_in = match.group(1) if match else (collection_input or "").strip()
        collection_id = None
        nome_colecao = ""

        for c in colecoes:
            if c["id"] == col_in or c["handle"].lower() == col_in.lower():
                collection_id = c["id"]
                nome_colecao = c["title"]
                break

        if not collection_id:
            st.error("Coleção não encontrada. Revise o **ID/handle/URL** e tente novamente.")
            status.update(label="Coleção não encontrada", state="error")
            st.stop()

        status.update(label=f"Coleção encontrada: {nome_colecao}", state="complete")

    with st.status("Buscando produtos da coleção...", expanded=False) as status:
        produtos = buscar_produtos(base_url, headers, collection_id)
        if not produtos:
            st.warning("Nenhum produto encontrado nesta coleção.")
            status.update(label="Sem produtos", state="error")
            st.stop()
        status.update(label=f"{len(produtos)} produtos encontrados", state="complete")

    # Prepare data
    dados = []
    os.makedirs("imagens_baixadas", exist_ok=True)
    tarefas = []

    for p in produtos:
        title = p.get("title", "")
        imagens = [img["src"] for img in p.get("images", [])]  # todas as imagens principais do produto
        item = {"Título": title}
        for i, img in enumerate(imagens):
            item[f"Imagem {i+1}"] = img
            if "📦" in modo:
                pasta = os.path.join("imagens_baixadas", re.sub(r'[\\/*?:\"<>|]', "_", title))
                os.makedirs(pasta, exist_ok=True)
                tarefas.append((img, os.path.join(pasta, f"{i+1}.jpg")))
        dados.append(item)

    # Execute downloads if needed
    if "📦" in modo:
        st.info(f"Baixando {len(tarefas)} imagens...")
        if turbo:
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
                list(ex.map(lambda x: baixar_imagem(*x), tarefas))
        else:
            for t in tarefas:
                baixar_imagem(*t)

        zip_name = f"imagens_colecao_{collection_id}.zip"
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk("imagens_baixadas"):
                for file in files:
                    path = os.path.join(root, file)
                    zipf.write(path, os.path.relpath(path, "imagens_baixadas"))

        with open(zip_name, "rb") as f:
            st.download_button("📥 Baixar ZIP", f, file_name=zip_name, use_container_width=True)

    # CSV
    csv_name = f"imagens_colecao_{collection_id}.csv"
    pd.DataFrame(dados).to_csv(csv_name, index=False, encoding="utf-8-sig")
    with open(csv_name, "rb") as f:
        st.download_button("📥 Baixar CSV", f, file_name=csv_name, use_container_width=True)

    st.success("🎉 Exportação concluída!")
