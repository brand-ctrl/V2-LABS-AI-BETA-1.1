import streamlit as st
import pandas as pd
import requests, os, io, zipfile, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

def render():
    st.markdown("""
    <div style="display:flex; align-items:center; gap:18px; margin: 8px 0 12px 0;">
        <img src="assets/icon_extrator.svg" width="250" style="flex-shrink:0;">
        <span style="font-size: 34px; font-weight: 800; letter-spacing: .5px; display:flex; align-items:center;">
            EXTRATOR DE IMAGENS CSV
        </span>
    </div>
    """, unsafe_allow_html=True)

    up = st.file_uploader("Envie o arquivo CSV", type=["csv"])
    col = st.text_input("Nome da coluna de URLs", "url")
    if not up: st.stop()

    try:
        df = pd.read_csv(up)
    except Exception:
        up.seek(0); df = pd.read_csv(up, sep=";")

    if col not in df.columns:
        st.error(f"Coluna '{col}' não encontrada. Colunas: {list(df.columns)}"); st.stop()

    urls = [u for u in df[col].astype(str).tolist() if u.startswith("http")]
    if not urls: st.warning("Nenhuma URL válida."); st.stop()

    OUT = "csv_out"; shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)
    prog = st.progress(0.0); info = st.empty()

    def fetch(iu):
        i,u = iu
        try:
            r=requests.get(u,timeout=25); r.raise_for_status()
            ext=".jpg"; ct=r.headers.get("content-type","")
            if "png" in ct: ext=".png"
            if "webp" in ct: ext=".webp"
            fn=f"img_{i:05d}{ext}"
            open(os.path.join(OUT,fn),"wb").write(r.content)
            return fn
        except Exception as e:
            return f"erro_{i}.txt"

    with ThreadPoolExecutor(max_workers=16) as ex:
        fut=[ex.submit(fetch, iu) for iu in enumerate(urls)]
        tot=len(fut)
        for i,f in enumerate(as_completed(fut),1):
            prog.progress(i/tot); info.info(f"Baixado {i}/{tot}")

    zbytes = io.BytesIO()
    with zipfile.ZipFile(zbytes,"w",zipfile.ZIP_DEFLATED) as z:
        for root,_,files in os.walk(OUT):
            for fn in files:
                fp=os.path.join(root,fn); arc=os.path.relpath(fp,OUT); z.write(fp,arc)
    zbytes.seek(0)
    st.success("Imagens extraídas com sucesso!")
    st.download_button("Baixar imagens", data=zbytes, file_name="imagens_csv.zip", mime="application/zip")
