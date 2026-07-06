from pathlib import Path
import sys
import traceback
from zipfile import ZipFile, ZIP_DEFLATED
import streamlit as st

from status_inteligente import (
    build_status_data,
    create_control_workbook,
    add_extra_files_to_zip,
)

APP_TITLE = "LicitaSuite Web 2.0"
APP_MAIN_TITLE = "Gerador de Atas de Registro de Preços"
APP_FOOTER = "LicitaSuite Web 2.0 • Desenvolvido por Januária Medeiros"

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
    for folder in [ATAS_DIR, OUTPUT_DIR, BASE_DIR / "atas_geradas", BASE_DIR / "output" / "atas_geradas"]:
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
:root{--blue:#0A4DC2;--blue2:#175BDF;--purple:#6742E6;--red:#EC174C;--text:#0B153D;--muted:#566482;--border:#DCE6F7;--shadow:0 16px 42px rgba(6,26,88,.10);}
.stApp{background:radial-gradient(circle at 86% 4%,rgba(103,66,230,.10),transparent 22%),linear-gradient(180deg,#FBFDFF 0%,#F2F7FF 100%);color:var(--text);}
header[data-testid="stHeader"]{height:0;background:transparent;}
.block-container{max-width:1180px;padding-top:.8rem;padding-bottom:0;}
.ls-header{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:0 0 18px 0;border-bottom:1px solid rgba(220,230,247,.95);}
.ls-logo img{width:min(330px,30vw);min-width:245px;height:auto;display:block;}
.ls-header-right{display:flex;align-items:center;gap:14px;color:#111827;font-size:18px;font-weight:600;white-space:nowrap;}
.ls-pill{background:#ECEEF2;color:#333A46;border-radius:999px;padding:9px 18px;font-size:14px;font-weight:700;}
.ls-hero{text-align:center;padding:38px 0 32px 0;}
.ls-system{color:var(--blue);letter-spacing:.42em;text-transform:uppercase;font-size:13px;font-weight:850;margin-bottom:18px;}
.ls-title{margin:0;color:#111;font-weight:900;text-transform:uppercase;letter-spacing:-.8px;line-height:1.05;font-size:clamp(28px,3.1vw,40px);white-space:nowrap;}
.ls-line{height:5px;width:min(760px,72%);margin:26px auto 0;border-radius:999px;background:linear-gradient(90deg,var(--blue2) 0%,var(--blue2) 36%,var(--red) 36%,var(--red) 58%,var(--purple) 58%,var(--purple) 100%);}
.ls-grid{display:grid;grid-template-columns:minmax(0,.82fr) minmax(0,1.18fr);gap:26px;align-items:stretch;}
.ls-card{background:rgba(255,255,255,.94);border:1px solid rgba(220,230,247,.98);border-radius:22px;box-shadow:var(--shadow);padding:28px;}
.ls-card-title-row{display:flex;align-items:flex-start;gap:14px;margin-bottom:20px;}
.ls-icon-round{width:50px;height:50px;border-radius:50%;background:linear-gradient(135deg,var(--blue2),var(--purple));color:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 12px 22px rgba(103,66,230,.22);flex:0 0 auto;}
.ls-card h2{margin:0;color:var(--text);font-size:23px;font-weight:850;text-transform:uppercase;letter-spacing:-.2px;}
.ls-card p{margin:10px 0 0;color:var(--muted);font-size:15px;line-height:1.55;}
.ls-upload-area{border:1.5px dashed #B9C9F4;border-radius:20px;padding:38px 22px;margin-top:22px;text-align:center;background:linear-gradient(180deg,#fff,#F8FBFF);}
.ls-upload-title{font-size:18px;color:var(--text);font-weight:850;margin-bottom:5px;}
.ls-upload-sub,.ls-upload-meta{color:var(--muted);font-size:15px;}
.ls-upload-meta{font-size:14px;margin-top:16px;}
.ls-security{margin-top:22px;background:linear-gradient(90deg,rgba(238,245,255,.95),rgba(248,246,255,.95));border:1px solid rgba(220,230,247,.98);border-radius:16px;padding:16px 18px;color:var(--blue);font-size:14px;display:flex;align-items:center;gap:11px;}
.ls-status-head{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:20px;}
.ls-status-pill{background:#F1EDFF;color:var(--purple);border-radius:999px;padding:9px 14px;font-size:13px;font-weight:850;white-space:nowrap;}
.ls-preview{border-top:1px solid var(--border);padding-top:20px;margin-top:14px;}
.ls-preview-title{color:var(--blue);font-weight:900;font-size:18px;text-transform:uppercase;margin-bottom:8px;}
.ls-preview-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px;}
.ls-mini-card{border:1px solid var(--border);border-radius:17px;padding:18px;background:linear-gradient(180deg,#fff,#F7FAFF);min-height:150px;}
.ls-mini-card.danger{border-color:#F5C9D3;background:linear-gradient(180deg,#fff,#FFF6F8);}
.ls-mini-title{font-weight:900;color:var(--blue);font-size:15px;margin-bottom:14px;}
.ls-mini-card.danger .ls-mini-title{color:#D0002B;}
.ls-example-line{display:flex;justify-content:space-between;gap:12px;font-size:14px;margin:9px 0;color:var(--text);}
.ls-footer{margin-top:30px;padding:18px 30px;text-align:center;color:rgba(255,255,255,.9);background:linear-gradient(90deg,#073F9E 0%,#4F39D7 72%,#7A44E8 100%);border-radius:14px 14px 0 0;border-top:3px solid var(--red);font-size:14px;}
div[data-testid="stFileUploader"] section{border:0!important;background:transparent!important;padding:0!important;}
div[data-testid="stFileUploader"] button{background:linear-gradient(135deg,var(--blue2),var(--purple))!important;color:white!important;border:none!important;border-radius:12px!important;font-weight:800!important;padding:.7rem 1.4rem!important;box-shadow:0 12px 24px rgba(103,66,230,.22)!important;}
.stButton>button{background:linear-gradient(135deg,var(--blue2),var(--purple));color:white;border:none;border-radius:13px;min-height:54px;font-weight:900;font-size:15px;box-shadow:0 15px 28px rgba(103,66,230,.24);text-transform:uppercase;}
.stButton>button:hover{background:linear-gradient(135deg,#073F9E,#5639DE);color:white;}
@media(max-width:900px){.block-container{padding-left:1rem;padding-right:1rem}.ls-header{flex-direction:column;align-items:flex-start;gap:12px}.ls-logo img{width:260px;min-width:220px}.ls-header-right{font-size:15px}.ls-hero{padding-top:28px}.ls-title{white-space:normal;font-size:30px}.ls-system{letter-spacing:.24em;font-size:11px}.ls-grid,.ls-preview-grid{grid-template-columns:1fr}}
</style>
""", unsafe_allow_html=True)

def render_header():
    st.markdown('<header class="ls-header">', unsafe_allow_html=True)
    if LOGO_PATH.exists():
        st.markdown('<div class="ls-logo">', unsafe_allow_html=True)
        st.image(str(LOGO_PATH))
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ls-logo" style="font-size:28px;font-weight:900;color:#073F9E;">ICISMEP CL</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ls-header-right"><span>{APP_TITLE}</span><span class="ls-pill">Uso Interno</span></div></header>', unsafe_allow_html=True)

def render_preview(status_data):
    fornecedores = status_data.get("fornecedores", [])
    itens_nao = status_data.get("itens_sem_vencedor", [])

    if not fornecedores and not itens_nao:
        return """
        <div class="ls-preview">
            <div class="ls-preview-title">Prévia da geração</div>
            <p>Após o envio, você verá as atas identificadas e os itens correspondentes.</p>
            <div class="ls-preview-grid">
                <div class="ls-mini-card"><div class="ls-mini-title">✓ Atas identificadas</div><div style="color:#566482;">Aguardando processamento.</div></div>
                <div class="ls-mini-card danger"><div class="ls-mini-title">✕ Itens não localizados</div><div style="color:#566482;">Aguardando processamento.</div></div>
            </div>
        </div>
        """

    linhas = []
    for idx, f in enumerate(fornecedores, start=1):
        nome = f.get("nome") or f.get("fornecedor") or f.get("contratado") or f"Fornecedor {idx}"
        itens = f.get("itens", [])
        itens_txt = ", ".join(str(i) for i in itens) if isinstance(itens, list) else str(itens)
        linhas.append(f'<div class="ls-example-line"><strong>ATA {idx:03d}</strong><span>{nome} — Itens: {itens_txt or "-"}</span></div>')

    itens_txt = ", ".join(str(i) for i in itens_nao) if itens_nao else "Nenhum item sem localização."

    return f"""
    <div class="ls-preview">
        <div class="ls-preview-title">Prévia da geração</div>
        <p>Dados identificados pelo motor do LicitaSuite.</p>
        <div class="ls-preview-grid">
            <div class="ls-mini-card">
                <div class="ls-mini-title">✓ Atas identificadas</div>
                {''.join(linhas)}
                <div style="margin-top:14px;color:#073F9E;font-weight:850;font-size:14px;">Total: {len(fornecedores)} atas</div>
            </div>
            <div class="ls-mini-card danger">
                <div class="ls-mini-title">✕ Itens não localizados</div>
                <div style="font-weight:850;color:#0B153D;font-size:15px;">{itens_txt}</div>
                <div style="margin-top:54px;color:#EC174C;font-weight:850;font-size:14px;">Total: {len(itens_nao)} itens</div>
            </div>
        </div>
    </div>
    """

def main():
    st.set_page_config(page_title="LicitaSuite Web", page_icon="📁", layout="wide")
    inject_css()
    render_header()

    st.markdown(f'<section class="ls-hero"><div class="ls-system">{APP_TITLE}</div><h1 class="ls-title">{APP_MAIN_TITLE}</h1><div class="ls-line"></div></section>', unsafe_allow_html=True)

    if "status_data" not in st.session_state:
        st.session_state.status_data = None

    col_upload, col_status = st.columns([0.9, 1.12], gap="large")

    with col_upload:
        st.markdown('<div class="ls-card"><div class="ls-card-title-row"><div class="ls-icon-round">↥</div><div><h2>1. Enviar processo</h2><p>Selecione o arquivo ZIP do processo.</p></div></div><div class="ls-upload-area"><div class="ls-upload-title">Arraste e solte o arquivo aqui</div><div class="ls-upload-sub">ou clique para selecionar</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Selecione o ZIP do processo", type=["zip"], label_visibility="collapsed")
        st.markdown('<div class="ls-upload-meta">Formato: ZIP • Tamanho máximo: 200MB</div></div><div class="ls-security">▣ Seus dados são processados localmente e não são armazenados.</div></div>', unsafe_allow_html=True)

    with col_status:
        preview_html = render_preview(st.session_state.status_data or {})
        st.markdown(f"""
        <div class="ls-card">
            <div class="ls-status-head">
                <div class="ls-card-title-row" style="margin-bottom:0;">
                    <div class="ls-icon-round">▤</div>
                    <div><h2>2. Status e prévia</h2><p>Acompanhe o progresso da geração em tempo real.</p></div>
                </div>
                <div class="ls-status-pill">● Status inteligente</div>
            </div>
            {preview_html}
        </div>
        """, unsafe_allow_html=True)

    generate_clicked = st.button("Iniciar geração", use_container_width=True)

    if uploaded_file is not None:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = UPLOAD_DIR / uploaded_file.name
        zip_path.write_bytes(uploaded_file.getbuffer())
        st.success(f"Arquivo recebido: {uploaded_file.name}")

        if generate_clicked:
            progress = st.progress(0)
            try:
                st.markdown("✓ Extraindo arquivos do ZIP")
                st.markdown("✓ Localizando motor do LicitaSuite")
                module_name, attr_name, engine_attr = find_engine()
                st.markdown(f"✓ Motor localizado: `{module_name}.{attr_name}`")
                progress.progress(20)

                st.markdown("✓ Processando documentos")
                result = run_engine(engine_attr, zip_path)
                progress.progress(70)

                if hasattr(result, "messages"):
                    for msg in result.messages:
                        st.markdown(f"✓ {msg}")

                if hasattr(result, "errors") and result.errors:
                    for err in result.errors:
                        st.error(err)

                files = collect_generated_docx()
                progress.progress(85)

                if not files:
                    st.error("O motor terminou, mas nenhuma Ata DOCX foi localizada em output/atas_geradas.")
                else:
                    st.markdown("✓ Gerando planilha de controle")
                    status_data = build_status_data(result, OUTPUT_DIR, files)
                    st.session_state.status_data = status_data

                    controle_path = create_control_workbook(status_data, OUTPUT_DIR)
                    zip_final = make_download_zip(files)
                    add_extra_files_to_zip(zip_final, [controle_path])

                    progress.progress(100)

                    st.success(f"{len(files)} ata(s) gerada(s).")
                    st.info(
                        f"Resumo: {status_data.get('total_atas', 0)} ata(s), "
                        f"{status_data.get('total_itens', 0)} item(ns) processado(s), "
                        f"{status_data.get('total_itens_nao_localizados', 0)} item(ns) não localizado(s)."
                    )

                    with open(zip_final, "rb") as f:
                        st.download_button("Baixar ZIP com Atas e Controle", f, "atas_geradas.zip", "application/zip", use_container_width=True)

                    st.rerun()

            except Exception as exc:
                st.error("Ocorreu um erro durante a geração.")
                st.error(str(exc))
                with st.expander("Traceback"):
                    st.code(traceback.format_exc())

    st.markdown(f'<div class="ls-footer">{APP_FOOTER}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
