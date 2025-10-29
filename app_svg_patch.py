# PATCH: replace your current app.py content with this if quiser usar os SVGs
import streamlit as st
from modules.conversor import render as render_conversor
from modules.extrator_csv import render as render_extrator

st.set_page_config(page_title="V2 LABS AI BETA", page_icon="🧪", layout="wide")

st.markdown("""
<style>
:root { --grad-start:#15aaff; --grad-end:#007bff; }
html, body, [class^="css"] { background: linear-gradient(135deg, rgba(21,170,255,0.05), rgba(0,123,255,0.05)); }
.v2-header { display:flex; align-items:center; gap:14px; margin: 8px 0 18px 0; }
.v2-brand { font-weight:800; letter-spacing:.5px; font-size:24px;
  background: linear-gradient(90deg, var(--grad-start), var(--grad-end));
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.v2-card { border-radius:14px; padding:14px 16px; background:#fff; box-shadow: 0 8px 24px rgba(0,0,0,.06);
  border:1px solid rgba(0,0,0,.05); transition: transform .15s ease, box-shadow .15s ease; }
.v2-card:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(0,0,0,.09);}
.v2-card h4 {margin:6px 0 6px; font-weight:700;} .v2-card p {margin:0; color:#556; font-size:0.92rem;}
.v2-card .icon {width:48px; height:48px; border-radius:12px; object-fit:cover;}
.navbar {display:flex; gap:8px; flex-wrap:wrap; margin: 8px 0 8px;}
</style>
""", unsafe_allow_html=True)

with st.container():
    cols = st.columns([1,6,1])
    with cols[1]:
        st.markdown(
            '<div class="v2-header">'
            '<img src="assets/logo_v2labs.svg" height="50"/>'
            '<div class="v2-brand">V2 LABS AI BETA</div>'
            '</div>',
            unsafe_allow_html=True
        )

if "route" not in st.session_state:
    st.session_state.route = "home"
def go(r): st.session_state.route = r

col1, col2, _ = st.columns([1,1,6])
with col1:
    if st.button("🏠 Home", type="secondary"): go("home")
with col2:
    if st.button("ℹ️ Sobre", type="secondary"): go("about")

route = st.session_state.route

if route == "home":
    st.subheader("Ferramentas")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="v2-card">'
            '<img class="icon" src="assets/icon_conversor.svg">'
            '<h4>Conversor de Imagens</h4>'
            '<p>Redimensione para 1080×1080 ou 1080×1920, com cor de fundo ou remoção de fundo.</p>'
            '</div>', unsafe_allow_html=True
        )
        if st.button("Abrir Conversor", key="btn_conv"): go("conversor")
    with c2:
        st.markdown(
            '<div class="v2-card">'
            '<img class="icon" src="assets/icon_extrator.svg">'
            '<h4>Extrair Imagens via CSV</h4>'
            '<p>Baixe imagens diretamente de URLs em CSV.</p>'
            '</div>', unsafe_allow_html=True
        )
        if st.button("Abrir Extrator CSV", key="btn_ext"): go("extrator")
elif route == "conversor":
    render_conversor()
elif route == "extrator":
    render_extrator()
else:
    st.subheader("Sobre")
    st.write("🧠 **V2 LABS AI BETA** — suíte de ferramentas inteligentes para manipulação de imagens.")
    st.write("Inclui o **Conversor de Imagens** (com remoção de fundo e formatos 1080x1080/1080x1920) "
             "e o **Extrator CSV** (para baixar imagens de URLs automaticamente).")
    st.write("Desenvolvido com ❤️ pela equipe **V2 LABS AI**.")
