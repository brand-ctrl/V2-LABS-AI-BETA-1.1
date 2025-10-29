
import streamlit as st
from PIL import Image
import zipfile, io, os, shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from rembg import remove as rembg_remove
    REMBG = True
except Exception:
    REMBG = False

def _resize_and_center(img: Image.Image, target_size, bg_color=None):
    w, h = img.size
    scale = min(target_size[0]/w, target_size[1]/h)
    new_w, new_h = max(1,int(w*scale)), max(1,int(h*scale))
    img = img.resize((new_w,new_h), Image.Resampling.LANCZOS).convert("RGBA")
    if bg_color is None:
        canvas = Image.new("RGBA", target_size, (0,0,0,0))
    else:
        canvas = Image.new("RGB", target_size, bg_color)
    off = ((target_size[0]-new_w)//2, (target_size[1]-new_h)//2)
    canvas.paste(img, off, img)
    return canvas

def process_one(path: Path, target, mode_bg, bg_rgb, out_fmt):
    with Image.open(path) as im:
        im = im.convert("RGBA")
        if mode_bg == "Remover fundo" and REMBG:
            import io as _io
            buf = _io.BytesIO()
            im.save(buf, format="PNG")
            data = rembg_remove(buf.getvalue())
            im = Image.open(_io.BytesIO(data)).convert("RGBA")
        canvas = _resize_and_center(im, target, None if mode_bg=="Remover fundo" else bg_rgb)
        bio = io.BytesIO()
        if out_fmt.upper()=="JPG":
            canvas = canvas.convert("RGB")
            canvas.save(bio, format="JPEG", quality=92, optimize=True)
        else:
            canvas.save(bio, format="PNG", optimize=True)
        return bio.getvalue()

def render():
    st.subheader("🖼️ Conversor de Imagens")
    colA, colB = st.columns(2)
    with colA:
        target_label = st.radio("Resolução", ("1080x1080","1080x1920"), horizontal=True)
        target = (1080,1080) if target_label=="1080x1080" else (1080,1920)
    with colB:
        mode_bg = st.radio("Fundo", ("Preencher com cor","Remover fundo"), horizontal=True)
    bg_rgb = None
    if mode_bg=="Preencher com cor":
        hexcor = st.color_picker("Cor de fundo", "#f2f2f2")
        bg_rgb = tuple(int(hexcor.strip("#")[i:i+2],16) for i in (0,2,4))
    if mode_bg=="Remover fundo" and not REMBG:
        st.warning("⚠️ O pacote rembg não está disponível neste ambiente.")
    out_fmt = st.selectbox("Formato de saída", ("JPG","PNG"), index=0 if mode_bg=="Preencher com cor" else 1)

    files = st.file_uploader("Envie imagens ou ZIP", type=["jpg","jpeg","png","webp","zip"], accept_multiple_files=True)
    if not files: st.stop()

    INP, OUT = "conv_in", "conv_out"
    shutil.rmtree(INP, ignore_errors=True); shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(INP, exist_ok=True); os.makedirs(OUT, exist_ok=True)

    from zipfile import ZipFile, BadZipFile
    for f in files:
        if f.name.lower().endswith(".zip"):
            try:
                with ZipFile(io.BytesIO(f.read())) as z: z.extractall(INP)
            except BadZipFile: st.error(f"ZIP inválido: {f.name}")
        else:
            open(os.path.join(INP, f.name),"wb").write(f.read())

    paths = [p for p in Path(INP).rglob("*") if p.suffix.lower() in (".jpg",".jpeg",".png",".webp")]
    if not paths: st.warning("Nenhuma imagem encontrada."); st.stop()

    prog = st.progress(0.0); info = st.empty()

    def worker(p: Path):
        data = process_one(p, target, mode_bg, bg_rgb, out_fmt)
        rel = p.relative_to(INP)
        outp = Path(OUT)/rel
        outp = outp.with_suffix("." + ("jpg" if out_fmt.upper()=="JPG" else "png"))
        os.makedirs(outp.parent, exist_ok=True)
        open(outp,"wb").write(data)
        return str(rel)

    res=[]; 
    with ThreadPoolExecutor(max_workers=8) as ex:
        fut=[ex.submit(worker,p) for p in paths]; tot=len(fut)
        for i,f in enumerate(as_completed(fut),1):
            res.append(f.result()); prog.progress(i/tot); info.info(f"Processado {i}/{tot}")

    zbytes = io.BytesIO()
    with zipfile.ZipFile(zbytes,"w",zipfile.ZIP_DEFLATED) as z:
        for root,_,files in os.walk(OUT):
            for fn in files:
                fp=os.path.join(root,fn); arc=os.path.relpath(fp,OUT); z.write(fp,arc)
    zbytes.seek(0)
    st.success("✅ Conversão concluída!")
    st.download_button("⬇️ Baixar imagens convertidas", data=zbytes, file_name=f"convertidas_{target_label}.zip", mime="application/zip")
