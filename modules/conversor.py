import streamlit as st
from PIL import Image
import io, os, shutil, requests, zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = "288cff6e-acb5-4773-9b67-b6c78f4f5cb0"

def _resize_and_center(img: Image.Image, target_size, bg_color=None):
    w, h = img.size
    scale = min(target_size[0]/w, target_size[1]/h)
    new_w, new_h = max(1,int(w*scale)), max(1,int(h*scale))
    img = img.resize((new_w,new_h), Image.Resampling.LANCZOS)
    if bg_color is None:
        canvas = Image.new("RGBA", target_size, (0,0,0,0))
    else:
        canvas = Image.new("RGB", target_size, bg_color)
    off = ((target_size[0]-new_w)//2, (target_size[1]-new_h)//2)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    canvas.paste(img, off, img)
    return canvas

def _api_remove_bg(image_bytes: bytes, out_format: str, width=None, height=None):
    url = "https://api.rembg.com/rmbg"
    headers = {"x-api-key": API_KEY}
    files = {"image": ("image", image_bytes, "application/octet-stream")}
    data = {}
    if out_format:
        data["format"] = out_format.lower()
    if width: data["w"] = str(width)
    if height: data["h"] = str(height)
    data["exact_resize"] = "false"
    data["expand"] = "true"
    r = requests.post(url, headers=headers, files=files, data=data, timeout=90)
    if r.status_code == 200:
        return r.content
    else:
        raise RuntimeError(f"API error {r.status_code}: {r.text[:200]}")

def render():
    # ---------- CABEÇALHO COM ÍCONE ----------
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 14px; margin-bottom: 10px;'>
        <img src='app/assets/icon_conversor.svg' width='42'>
        <h1 style='margin: 0; font-size: 28px;'>CONVERSOR DE IMAGENS</h1>
    </div>
    """, unsafe_allow_html=True)

    # ---------- OPÇÕES PRINCIPAIS ----------
    col1, col2 = st.columns(2)
    with col1:
        target_label = st.radio("Resolução", ("1080x1080", "1080x1920"), horizontal=True)
        target = (1080,1080) if target_label=="1080x1080" else (1080,1920)
    with col2:
        mode = st.radio("Modo", ("Preencher com cor", "Remover Fundo (API)"), horizontal=True)

    bg_rgb = None
    if mode == "Preencher com cor":
        hexcor = st.color_picker("Cor de fundo", "#f2f2f2")
        bg_rgb = tuple(int(hexcor.strip("#")[i:i+2],16) for i in (0,2,4))

    st.write("---")
    out_format = st.selectbox("Formato de saída", ("png", "jpg", "webp"), index=0)

    # ---------- UPLOAD ----------
    files = st.file_uploader("Envie imagens ou ZIP", type=["jpg","jpeg","png","webp","zip"], accept_multiple_files=True)
    if not files:
        st.stop()

    INP, OUT = "conv_in", "conv_out"
    shutil.rmtree(INP, ignore_errors=True); shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(INP, exist_ok=True); os.makedirs(OUT, exist_ok=True)

    from zipfile import ZipFile, BadZipFile
    for f in files:
        if f.name.lower().endswith(".zip"):
            try:
                with ZipFile(io.BytesIO(f.read())) as z: z.extractall(INP)
            except BadZipFile:
                st.error(f"Arquivo ZIP inválido: {f.name}")
        else:
            open(os.path.join(INP, f.name), "wb").write(f.read())

    paths = [p for p in Path(INP).rglob("*") if p.suffix.lower() in (".jpg",".jpeg",".png",".webp")]
    if not paths:
        st.warning("Nenhuma imagem encontrada.")
        st.stop()

    prog = st.progress(0.0)
    info = st.empty()
    results = []

    def worker(p: Path):
        rel = p.relative_to(INP)
        raw = open(p, "rb").read()

        if mode == "Remover Fundo (API)":
            api_bytes = _api_remove_bg(raw, out_format="png")
            img = Image.open(io.BytesIO(api_bytes)).convert("RGBA")
            composed = _resize_and_center(img, target, bg_color=None)
        else:
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
            composed = _resize_and_center(img, target, bg_color=bg_rgb)

        outp = (Path(OUT)/rel).with_suffix("." + out_format.lower())
        os.makedirs(outp.parent, exist_ok=True)
        bio = io.BytesIO()
        if out_format.lower() == "jpg":
            composed.convert("RGB").save(bio, format="JPEG", quality=92, optimize=True)
        elif out_format.lower() == "png":
            composed.save(bio, format="PNG", optimize=True)
        else:
            composed.save(bio, format="WEBP", quality=95)
        open(outp, "wb").write(bio.getvalue())

        prev_io = io.BytesIO()
        pv = composed.copy()
        pv.thumbnail((360, 360))
        if out_format.lower() == "jpg":
            pv.convert("RGB").save(prev_io, format="JPEG", quality=85); mime = "image/jpeg"
        elif out_format.lower() == "png":
            pv.save(prev_io, format="PNG"); mime = "image/png"
        else:
            pv.save(prev_io, format="WEBP", quality=90); mime = "image/webp"
        return rel.as_posix(), prev_io.getvalue(), mime

    with ThreadPoolExecutor(max_workers=8) as ex:
        fut = [ex.submit(worker, p) for p in paths]
        tot = len(fut)
        for i, f in enumerate(as_completed(fut), 1):
            try:
                results.append(f.result())
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
            prog.progress(i/tot)
            info.info(f"Processado {i}/{tot}")

    st.write("---")
    st.subheader("Pré-visualizações")
    cols = st.columns(3)
    for idx, (name, data, mime) in enumerate(results[:6]):
        with cols[idx % 3]:
            st.image(data, caption=name, use_column_width=True)

    zbytes = io.BytesIO()
    with zipfile.ZipFile(zbytes, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(OUT):
            for fn in files:
                fp = os.path.join(root, fn)
                arc = os.path.relpath(fp, OUT)
                z.write(fp, arc)
    zbytes.seek(0)

    st.success("Conversão concluída!")
    st.download_button(
        "Baixar imagens convertidas",
        data=zbytes,
        file_name=f"convertidas_{target_label}.zip",
        mime="application/zip"
    )
