from pathlib import Path
import sys
import traceback
from zipfile import ZipFile, ZIP_DEFLATED
import streamlit as st

APP_TITLE = "LicitaSuite Web 1.0"
APP_MAIN_TITLE = "Gerador de Atas de Registro de Preços"
APP_VERSION = "Versão Web 1.0 Free"
APP_FOOTER = "LicitaSuite Web 1.0 • Desenvolvido por Januária Medeiros"

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
:root{
--azul-noite:#071B59;--azul-ic:#073F9E;--azul-vivo:#1457D9;--violeta:#6D4CFF;--lilas:#A58CFF;
--vermelho:#EC174C;--texto:#0B153D;--muted:#53617E;--borda:#DCE6F7;
}
.stApp{background:radial-gradient(circle at 85% 5%,rgba(109,76,255,.16),transparent 24%),radial-gradient(circle at 16% 8%,rgba(20,87,217,.12),transparent 26%),linear-gradient(180deg,#FBFDFF 0%,#F2F7FF 100%);color:var(--texto);}
header[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:1220px;padding-top:0;padding-bottom:0;}
.ls-layout{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:100vh;margin:0 -2rem;}
.ls-sidebar{background:radial-gradient(circle at 10% 100%,rgba(109,76,255,.55),transparent 35%),linear-gradient(180deg,#06226F 0%,#071B59 58%,#0A1B4C 100%);color:white;padding:34px 24px 26px;position:relative;overflow:hidden;box-shadow:18px 0 50px rgba(7,27,89,.18);}
.ls-logo-block{margin-bottom:42px;position:relative;z-index:2}.ls-logo-block img{width:185px;max-width:100%;height:auto;display:block}
.ls-menu{display:flex;flex-direction:column;gap:12px;position:relative;z-index:2}
.ls-menu-item{display:flex;align-items:center;gap:13px;padding:14px 15px;border-radius:14px;color:rgba(255,255,255,.88);font-weight:700;font-size:15px}
.ls-menu-item.active{background:linear-gradient(135deg,#1457D9,#6D4CFF);color:white;box-shadow:0 15px 26px rgba(20,87,217,.28)}
.ls-sidebar-note{position:absolute;left:24px;right:24px;bottom:30px;z-index:3;border:1px solid rgba(255,255,255,.17);background:rgba(255,255,255,.075);border-radius:16px;padding:16px;font-size:13px;line-height:1.55;color:rgba(255,255,255,.84)}
.ls-main{padding:28px 34px 0;min-width:0}.ls-top{display:flex;justify-content:space-between;align-items:center;padding-bottom:26px}
.ls-org{color:var(--azul-noite);font-size:15px;line-height:1.45;font-weight:600}.ls-help{display:flex;align-items:center;gap:22px;color:var(--azul-noite);font-weight:700;font-size:14px}
.ls-avatar{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,var(--azul-vivo),var(--violeta));display:flex;align-items:center;justify-content:center;color:white;font-weight:800;box-shadow:0 12px 24px rgba(20,87,217,.22)}
.ls-hero{text-align:center;padding:34px 0 30px}.ls-system{color:var(--azul-vivo);letter-spacing:.44em;text-transform:uppercase;font-size:13px;font-weight:800;margin-bottom:14px}
.ls-title{margin:0;font-size:clamp(38px,4.9vw,57px);line-height:1.05;letter-spacing:-1.2px;color:var(--azul-noite);font-weight:900;text-transform:uppercase}
.ls-line{height:5px;width:min(820px,86%);margin:24px auto 0;border-radius:999px;background:linear-gradient(90deg,var(--azul-vivo) 0%,var(--azul-vivo) 38%,var(--vermelho) 38%,var(--vermelho) 58%,var(--violeta) 58%,var(--violeta) 100%);box-shadow:0 9px 22px rgba(20,87,217,.12)}
.ls-grid{display:grid;grid-template-columns:minmax(0,.95fr) minmax(0,1.1fr);gap:24px;margin-top:6px}
.ls-card{background:rgba(255,255,255,.94);border:1px solid rgba(220,230,247,.95);border-radius:22px;box-shadow:0 22px 60px rgba(7,27,89,.12);padding:28px;backdrop-filter:blur(12px)}
.ls-card-title-row{display:flex;align-items:flex-start;gap:14px;margin-bottom:18px}.ls-step{width:36px;height:36px;border-radius:50%;color:white;background:linear-gradient(135deg,var(--azul-vivo),var(--violeta));display:flex;align-items:center;justify-content:center;font-weight:900;flex:0 0 auto;box-shadow:0 12px 20px rgba(109,76,255,.24)}
.ls-card h2{margin:0;color:var(--azul-noite);font-size:20px;font-weight:850;text-transform:uppercase}.ls-card p{margin:6px 0 0;color:var(--muted);font-size:14px;line-height:1.45}
.ls-upload-area{border:1.5px dashed #B9C9F4;border-radius:19px;padding:28px 20px;margin-top:20px;text-align:center;background:linear-gradient(180deg,rgba(255,255,255,.9),rgba(247,250,255,.88))}
.ls-cloud{font-size:52px;line-height:1;color:var(--violeta);margin-bottom:8px}.ls-security{margin-top:18px;background:linear-gradient(90deg,rgba(238,245,255,.9),rgba(248,246,255,.9));border:1px solid rgba(220,230,247,.9);border-radius:14px;padding:13px 15px;color:var(--azul-ic);font-size:13px;display:flex;align-items:center;gap:10px}
.ls-status-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px}.ls-pill{background:#F1EDFF;color:var(--violeta);border-radius:999px;padding:8px 13px;font-size:12px;font-weight:800;white-space:nowrap}
.ls-preview{border-top:1px solid var(--borda);padding-top:18px;margin-top:14px}.ls-preview-title{color:var(--azul-vivo);font-weight:850;font-size:17px;text-transform:uppercase;margin-bottom:8px}
.ls-preview-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:14px}.ls-mini-card{border:1px solid var(--borda);border-radius:16px;padding:16px;background:linear-gradient(180deg,#fff,#F7FAFF);min-height:130px}.ls-mini-card.danger{border-color:#F5C9D3;background:linear-gradient(180deg,#fff,#FFF6F8)}
.ls-mini-title{font-weight:850;color:var(--azul-noite);font-size:14px;margin-bottom:12px}.ls-mini-card.danger .ls-mini-title{color:#B40024}.ls-example-line{display:flex;justify-content:space-between;gap:12px;font-size:13px;margin:8px 0;color:var(--azul-noite)}
.ls-benefits{border-top:1px solid var(--borda);margin-top:18px;padding-top:16px}.ls-benefit{display:grid;grid-template-columns:34px minmax(0,1fr);gap:12px;padding:10px 0;border-bottom:1px solid #EEF2FA}.ls-benefit:last-child{border-bottom:none}.ls-benefit-icon{color:var(--azul-vivo);font-size:22px}.ls-benefit strong{color:var(--azul-noite);font-size:14px}.ls-benefit div:last-child{color:var(--muted);font-size:13px;line-height:1.4}
.ls-bottom-call{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:center;margin-top:22px;background:linear-gradient(90deg,rgba(255,255,255,.96),rgba(247,243,255,.92));border:1px solid var(--borda);border-radius:19px;box-shadow:0 18px 38px rgba(7,27,89,.08);padding:22px 26px}.ls-bottom-call strong{color:var(--azul-noite);font-size:17px}.ls-bottom-call span{color:var(--muted);display:block;margin-top:5px;font-size:14px}
.ls-footer{margin:26px -34px 0;padding:18px 34px;text-align:center;color:rgba(255,255,255,.86);background:linear-gradient(90deg,#073F9E 0%,#4F39D7 72%,#7A44E8 100%);border-top:3px solid var(--vermelho);font-size:13.5px}
div[data-testid="stFileUploader"] section{border:0!important;background:transparent!important;padding:0!important}div[data-testid="stFileUploader"] button{background:linear-gradient(135deg,var(--azul-vivo),var(--violeta))!important;color:white!important;border:none!important;border-radius:12px!important;font-weight:800!important;padding:.7rem 1.4rem!important;box-shadow:0 12px 24px rgba(109,76,255,.24)!important}
.stButton>button{background:linear-gradient(135deg,var(--azul-vivo),var(--violeta));color:white;border:none;border-radius:13px;min-height:50px;font-weight:900;font-size:15px;box-shadow:0 15px 28px rgba(109,76,255,.24);text-transform:uppercase}.stButton>button:hover{background:linear-gradient(135deg,#073F9E,#5639DE);color:white}
@media(max-width:900px){.ls-layout{display:block;margin:0 -1rem}.ls-sidebar{padding:22px;min-height:auto}.ls-sidebar-note,.ls-menu{display:none}.ls-logo-block{margin-bottom:0}.ls-logo-block img{width:160px}.ls-main{padding:22px 20px 0}.ls-top{display:none}.ls-grid,.ls-preview-grid,.ls-bottom-call{grid-template-columns:1fr}.ls-title{font-size:34px}.ls-system{letter-spacing:.25em;font-size:11px}.ls-footer{margin-left:-20px;margin-right:-20px}}
</style>
""", unsafe_allow_html=True)

def render_layout_start():
    st.markdown('<div class="ls-layout"><aside class="ls-sidebar">', unsafe_allow_html=True)
    if LOGO_PATH.exists():
        st.markdown('<div class="ls-logo-block">', unsafe_allow_html=True)
        st.image(str(LOGO_PATH), width=185)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ls-logo-block" style="font-size:28px;font-weight:900;">ICISMEP</div>', unsafe_allow_html=True)

    st.markdown("""
<nav class="ls-menu">
<div class="ls-menu-item active">⌂ <span>Início</span></div>
<div class="ls-menu-item">▤ <span>Processos</span></div>
<div class="ls-menu-item">◷ <span>Histórico</span></div>
<div class="ls-menu-item">▥ <span>Relatórios</span></div>
<div class="ls-menu-item">⚙ <span>Configurações</span></div>
<div class="ls-menu-item">ⓘ <span>Sobre o sistema</span></div>
</nav>
<div class="ls-sidebar-note"><strong>Ambiente seguro</strong><br>Seus dados são processados localmente e não são armazenados.</div>
</aside><main class="ls-main">
<div class="ls-top"><div class="ls-org">Diretoria de Compras,<br>Contratações e Logística</div><div class="ls-help">ⓘ Ajuda <span class="ls-avatar">JM</span></div></div>
""", unsafe_allow_html=True)

    st.markdown(f"""
<section class="ls-hero">
<div class="ls-system">{APP_TITLE}</div>
<h1 class="ls-title">{APP_MAIN_TITLE}</h1>
<div class="ls-line"></div>
</section>
""", unsafe_allow_html=True)

def render_footer():
    st.markdown(f'<div class="ls-footer">{APP_FOOTER}</div></main></div>', unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="LicitaSuite Web", page_icon="📁", layout="wide")
    inject_css()
    render_layout_start()

    col_upload, col_status = st.columns([0.95, 1.18], gap="large")
    with col_upload:
        st.markdown("""
<div class="ls-card"><div class="ls-card-title-row"><div class="ls-step">1</div><div><h2>Enviar processo</h2><p>Selecione o arquivo ZIP do processo.<br>O sistema irá identificar os fornecedores e itens automaticamente.</p></div></div>
<div class="ls-upload-area"><div class="ls-cloud">☁</div><strong>Arraste e solte o arquivo aqui</strong><br><span style="color:#53617E;">ou clique para selecionar</span>
""", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Selecione o ZIP do processo", type=["zip"], label_visibility="collapsed")
        st.markdown("""<div style="margin-top:10px;color:#53617E;font-size:13px;">Formato: ZIP • Tamanho máximo: 200MB</div></div><div class="ls-security">▣ Seus dados são processados localmente e não são armazenados.</div></div>""", unsafe_allow_html=True)

    with col_status:
        st.markdown("""
<div class="ls-card"><div class="ls-status-head"><div class="ls-card-title-row" style="margin-bottom:0;"><div class="ls-step">2</div><div><h2>Status e prévia</h2><p>Acompanhe o progresso da geração em tempo real.</p></div></div><div class="ls-pill">● Aguardando envio</div></div>
<div class="ls-preview"><div class="ls-preview-title">Prévia da geração</div><p>Após o envio, você verá as atas identificadas e os itens correspondentes.</p>
<div class="ls-preview-grid">
<div class="ls-mini-card"><div class="ls-mini-title">✓ Atas identificadas</div><div class="ls-example-line"><strong>ATA 107</strong><span>Itens: 1, 2, 4, 5, 10</span></div><div class="ls-example-line"><strong>ATA 108</strong><span>Itens: 6, 7, 8, 11</span></div><div class="ls-example-line"><strong>ATA 109</strong><span>Itens: 12, 13, 14, 15</span></div><div style="margin-top:14px;color:#073F9E;font-weight:800;font-size:13px;">Total: 3 atas</div></div>
<div class="ls-mini-card danger"><div class="ls-mini-title">! Itens não localizados</div><div style="font-weight:800;color:#0B153D;font-size:14px;">2, 9, 10, 18</div><div style="margin-top:48px;color:#EC174C;font-weight:800;font-size:13px;">Total: 4 itens</div></div>
</div></div>
<div class="ls-benefits"><div class="ls-benefit"><div class="ls-benefit-icon">▣</div><div><strong>Seguro</strong><br>Processamento local. Seus dados não são armazenados.</div></div><div class="ls-benefit"><div class="ls-benefit-icon">ϟ</div><div><strong>Rápido</strong><br>Geração automática das atas com agilidade e precisão.</div></div><div class="ls-benefit"><div class="ls-benefit-icon">▤</div><div><strong>Confiável</strong><br>Baseado na versão desktop do LicitaSuite.</div></div></div></div>
""", unsafe_allow_html=True)

    st.markdown("""<div class="ls-bottom-call"><div><strong>Pronto para gerar suas atas?</strong><span>Envie o arquivo ZIP do processo para iniciar.</span></div>""", unsafe_allow_html=True)
    generate_clicked = st.button("▷ Iniciar geração", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_file is not None:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = UPLOAD_DIR / uploaded_file.name
        zip_path.write_bytes(uploaded_file.getbuffer())
        st.success(f"Arquivo recebido: {uploaded_file.name}")

        if generate_clicked:
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
                        st.download_button("Baixar ZIP com Atas", f, "atas_geradas.zip", "application/zip", use_container_width=True)
            except Exception as exc:
                st.error("Ocorreu um erro durante a geração.")
                st.error(str(exc))
                with st.expander("Traceback"):
                    st.code(traceback.format_exc())

    render_footer()

if __name__ == "__main__":
    main()
