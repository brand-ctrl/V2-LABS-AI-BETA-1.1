import streamlit as st
from PIL import Image
import io, os, shutil, zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from rembg import remove
    _HAS_REMBG = True
except Exception:
    _HAS_REMBG = False

def _remove_bg_bytes(img_bytes: bytes) -> bytes:
    return remove(img_bytes)

def render():
    st.markdown("""
    <div style="display:flex; align-items:center; gap:18px; margin: 8px 0 12px 0;">
        <img src="assets/icon_removedor.svg" width="250" style="flex-shrink:0;">
        <span style="font-size: 34px; font-weight: 800; letter-spacing: .5px; display:flex; align-items:center;">
            REMOVEDOR DE FUNDO
        </span>
    </div>
    """, unsafe_allow_html=True)

    if not _HAS_REMBG:
        st.error("Biblioteca 'rembg' não encontrada. Instale com: pip install rembg onnxruntime")
        st.stop()

    files = st.file_uploader("Envie imagens ou ZIP", type=["jpg","jpeg","png","webp","zip"], accept_multiple_files=True)
    if not files: st.stop()

    INP, OUT = "rm_in", "rm_out"
    shutil.rmtree(INP, ignore_errors=True); shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(INP, exist_ok=True); os.makedirs(OUT, exist_ok=True)

    from zipfile import ZipFile, BadZipFile
    for f in files:
        if f.name.lower().endswith(".zip"):
            try:
                with ZipFile(io.BytesIO(f.read())) as z: z.extractall(INP)
            except BadZipFile: st.error(f"ZIP inválido: {f.name}")
        else:
            open(os.path.join(INP, f.name), "wb").write(f.read())

    paths = [p for p in Path(INP).rglob("*") if p.suffix.lower() in (".jpg",".jpeg",".png",".webp")]
    if not paths:
        st.warning("Nenhuma imagem encontrada."); st.stop()

    prog = st.progress(0.0); info = st.empty()
    results = []

    def worker(p: Path):
        rel = p.relative_to(INP)
        raw = open(p, "rb").read()
        out_bytes = _remove_bg_bytes(raw)
        outp = (Path(OUT)/rel).with_suffix(".png")
        os.makedirs(outp.parent, exist_ok=True)
        open(outp, "wb").write(out_bytes)

        prev = Image.open(io.BytesIO(out_bytes)).convert("RGBA")
        prev.thumbnail((360,360))
        b = io.BytesIO(); prev.save(b, format="PNG"); b.seek(0)
        return rel.as_posix(), b.getvalue(), "image/png"

    from PIL import Image
    with ThreadPoolExecutor(max_workers=4) as ex:
        fut=[ex.submit(worker,p) for p in paths]; tot=len(fut)
        for i,f in enumerate(as_completed(fut),1):
            try: results.append(f.result())
            except Exception as e: st.error(f"Erro ao processar: {e}")
            prog.progress(i/tot); info.info(f"Processado {i}/{tot}")

    st.write("---"); st.subheader("Pré-visualizações")
    cols = st.columns(3)
    for idx, (name, data, mime) in enumerate(results[:6]):
        with cols[idx % 3]:
            st.image(data, caption=name, use_column_width=True)

    zbytes = io.BytesIO()
    with zipfile.ZipFile(zbytes, "w", zipfile.ZIP_DEFLATED) as z:
        for root,_,files in os.walk(OUT):
            for fn in files:
                fp=os.path.join(root,fn); arc=os.path.relpath(fp,OUT); z.write(fp,arc)
    zbytes.seek(0)
    st.success("Remoção de fundo concluída!")
    st.download_button("Baixar PNGs sem fundo", data=zbytes, file_name="sem_fundo.zip", mime="application/zip")
