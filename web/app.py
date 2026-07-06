from pathlib import Path
import sys
import traceback
from zipfile import ZipFile, ZIP_DEFLATED
import streamlit as st

APP_TITLE = "LicitaSuite Web 1.0"
APP_SUBTITLE = "Gerador de Atas de Registro de Preços"
APP_VERSION = "Versão Web 1.0 Free"
APP_FOOTER = "LicitaSuite Web • Desenvolvido por Januária Medeiros"

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "web_uploads"
OUTPUT_DIR = BASE_DIR / "output"
ATAS_DIR = OUTPUT_DIR / "atas_geradas"
LOGO_PATH = BASE_DIR / "assets" / "logo_icismep_cl.png"

def find_engine():
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    attempts = [
        ("licitasuite.engine.pipeline", "Pipeline"),
        ("licitasuite.motor.pipeline", "Pipeline"),
        ("licitasuite.motor.pipeline", "executar_pipeline"),
        ("licitasuite.motor.gerador", "gerar_atas"),
        ("licitasuite.geradores.pipeline", "Pipeline"),
        ("licitasuite.geradores.atas", "gerar_atas"),
    ]
    errors = []
    for module_name, attr_name in attempts:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            attr = getattr(module, attr_name)
            return module_name, attr_name, attr
        except Exception as exc:
            errors.append(f"{module_name}.{attr_name}: {exc}")
    raise RuntimeError("Não foi possível localizar o motor do LicitaSuite. Tentativas: " + " | ".join(errors))

def run_engine(engine_attr, zip_path):
    if isinstance(engine_attr, type):
        engine = engine_attr()
        for method_name in ["run", "process", "execute", "run_initial_scan"]:
            if hasattr(engine, method_name):
                return getattr(engine, method_name)(zip_path)
        raise RuntimeError("Motor localizado, mas nenhum método de execução foi encontrado.")
    if callable(engine_attr):
        return engine_attr(zip_path)
    raise RuntimeError("Motor localizado, mas não é executável.")

def collect_generated_docx():
    files = []
    for folder in [ATAS_DIR, OUTPUT_DIR, BASE_DIR / "atas_geradas"]:
        if folder.exists():
            files.extend(folder.rglob("*.docx"))
    return sorted({p.resolve() for p in files if not p.name.startswith("~$")})

def make_download_zip(files):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_final = OUTPUT_DIR / "atas_geradas.zip"
    if zip_final.exists():
        zip_final.unlink()
    with ZipFile(zip_final, "w", ZIP_DEFLATED) as z:
        for file in files:
            z.write(file, file.name)
    return zip_final

def inject_css():
    st.markdown("""
<style>
:root{--azul:#003B83;--azul2:#0B4EA2;--vermelho:#D80D2A;--texto:#0F172A;--cinza:#5B677A;}
.stApp{background:radial-gradient(circle at 92% 12%,rgba(11,78,162,.12),transparent 28%),linear-gradient(180deg,#F8FBFF 0%,#EEF5FF 100%);color:var(--texto);}
header[data-testid="stHeader"]{background:rgba(255,255,255,0);}
.block-container{max-width:1180px;padding-top:1.4rem;padding-bottom:0;}
.ls-topbar{background:#fff;border-radius:0 0 20px 20px;border-bottom:4px solid var(--azul);box-shadow:0 8px 26px rgba(0,45,105,.12);padding:22px 34px;margin:-18px -10px 38px -10px;position:relative;overflow:hidden;}
.ls-topbar:before{content:"";position:absolute;top:0;right:0;width:160px;height:18px;background:var(--vermelho);border-bottom-left-radius:70px;}
.ls-title{font-size:clamp(42px,6vw,72px);line-height:1.05;font-weight:800;color:var(--azul);margin:0;letter-spacing:-1.5px;}
.ls-redline{width:118px;height:6px;border-radius:8px;background:var(--vermelho);margin:22px 0 26px 0;}
.ls-subtitle{font-size:clamp(22px,3vw,34px);color:#4B5563;font-weight:500;margin:0 0 20px 0;}
.ls-card{background:#fff;border:1px solid rgba(221,232,247,.9);border-radius:22px;box-shadow:0 14px 32px rgba(0,45,105,.10);padding:30px 34px;margin-bottom:26px;}
.ls-section-head{display:flex;align-items:center;gap:18px;margin-bottom:12px;}
.ls-icon{width:62px;height:62px;border-radius:50%;background:linear-gradient(135deg,var(--azul),var(--azul2));display:flex;align-items:center;justify-content:center;color:#fff;font-size:30px;box-shadow:0 8px 18px rgba(0,59,131,.22);flex:0 0 auto;}
.ls-section-title{font-size:32px;color:var(--azul);font-weight:800;margin:0;}
.ls-section-sub{font-size:18px;color:var(--cinza);margin:3px 0 0 0;}
.ls-status-pill{background:#E7F1FF;color:var(--azul);border-radius:13px;padding:18px 20px;font-size:20px;font-weight:650;display:flex;align-items:center;gap:12px;margin:18px 0;}
.ls-ok{width:36px;height:36px;border-radius:50%;border:3px solid #18A957;color:#18A957;display:inline-flex;align-items:center;justify-content:center;font-weight:800;}
.ls-help{color:var(--cinza);font-size:17px;margin-top:4px;}
.ls-footer{margin:54px -20px 0 -20px;padding:28px 40px;min-height:72px;background:linear-gradient(90deg,#002D69,#004A9F);border-top:4px solid var(--vermelho);color:rgba(255,255,255,.86);font-size:15px;text-align:right;}
div[data-testid="stFileUploader"] section{border:2px dashed #9CC4F3!important;border-radius:18px!important;background:#FBFDFF!important;padding:34px 18px!important;}
div[data-testid="stFileUploader"] button{background:var(--azul)!important;color:white!important;border-radius:10px!important;border:none!important;font-weight:700!important;}
.stButton>button{background:linear-gradient(90deg,var(--azul),var(--azul2));color:#fff;border:none;border-radius:12px;font-weight:800;min-height:52px;font-size:18px;box-shadow:0 9px 18px rgba(0,59,131,.18);}
.stButton>button:hover{background:linear-gradient(90deg,#002D69,var(--azul));color:#fff;}
@media(max-width:720px){.block-container{padding-left:1.1rem;padding-right:1.1rem}.ls-card{padding:24px 22px}.ls-section-title{font-size:27px}.ls-icon{width:52px;height:52px;font-size:25px}.ls-footer{text-align:right;padding:24px 22px}}
</style>
""", unsafe_allow_html=True)

def render_header():
    st.markdown('<div class="ls-topbar">', unsafe_allow_html=True)
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=620)
    else:
        st.markdown('<div style="font-size:30px;font-weight:800;color:#003B83;">ICISMEP CL</div><div style="font-size:20px;color:#003B83;">Diretoria de Compras, Contratações e Logística</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="ls-title">{APP_TITLE}</h1><div class="ls-redline"></div><p class="ls-subtitle">{APP_SUBTITLE}</p>', unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="LicitaSuite Web", page_icon="📁", layout="wide")
    inject_css()
    render_header()

    col_upload, col_status = st.columns([1.45, .9], gap="large")
    with col_upload:
        st.markdown('<div class="ls-card"><div class="ls-section-head"><div class="ls-icon">▣</div><div><h2 class="ls-section-title">Enviar processo</h2><p class="ls-section-sub">Selecione o ZIP do processo</p></div></div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Selecione o ZIP do processo", type=["zip"], label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_status:
        st.markdown(f'<div class="ls-card"><div class="ls-section-head"><div class="ls-icon">i</div><div><h2 class="ls-section-title">Status</h2></div></div><div class="ls-status-pill"><span class="ls-ok">✓</span><span>{APP_VERSION}</span></div><div class="ls-help">Use o motor da versão desktop.</div></div>', unsafe_allow_html=True)

    if uploaded_file is not None:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = UPLOAD_DIR / uploaded_file.name
        zip_path.write_bytes(uploaded_file.getbuffer())
        st.success(f"Arquivo recebido: {uploaded_file.name}")

        if st.button("⚙️ GERAR ATAS", use_container_width=True):
            progress = st.progress(0)
            try:
                st.markdown("✓ Localizando motor do LicitaSuite...")
                module_name, attr_name, engine_attr = find_engine()
                st.markdown(f"✓ Motor localizado: `{module_name}.{attr_name}`")
                progress.progress(25)

                st.markdown("✓ Processando documentos...")
                result = run_engine(engine_attr, zip_path)
                progress.progress(70)

                if hasattr(result, "messages"):
                    for msg in result.messages:
                        st.markdown(f"✓ {msg}")
                if hasattr(result, "errors") and result.errors:
                    for err in result.errors:
                        st.error(err)

                files = collect_generated_docx()
                progress.progress(90)
                if not files:
                    st.error("O motor terminou, mas nenhuma Ata DOCX foi localizada em output/atas_geradas.")
                else:
                    zip_final = make_download_zip(files)
                    progress.progress(100)
                    st.success(f"{len(files)} ata(s) gerada(s).")
                    with open(zip_final, "rb") as f:
                        st.download_button("⬇️ Baixar ZIP com Atas", f, "atas_geradas.zip", "application/zip", use_container_width=True)
            except Exception as exc:
                st.error("Ocorreu um erro durante a geração.")
                st.error(str(exc))
                with st.expander("Traceback"):
                    st.code(traceback.format_exc())

    st.markdown(f'<div class="ls-footer">{APP_FOOTER}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
