import importlib
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
import streamlit as st

BASE_DIR = Path.cwd()
UPLOAD_DIR = BASE_DIR / "web_uploads"
OUTPUT_DIR = BASE_DIR / "output"
ATAS_DIR = OUTPUT_DIR / "atas_geradas"

st.set_page_config(page_title="LicitaSuite Web", page_icon="📘", layout="wide")


def ensure_dirs():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ATAS_DIR.mkdir(parents=True, exist_ok=True)


def clear_previous_outputs():
    ATAS_DIR.mkdir(parents=True, exist_ok=True)
    for item in ATAS_DIR.iterdir():
        try:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception:
            pass


def find_engine():
    candidates = [
        ("licitasuite.engine.pipeline", "Pipeline"),
        ("licitasuite.motor.pipeline", "Pipeline"),
        ("licitasuite.motor.pipeline", "executar_pipeline"),
        ("licitasuite.motor.pipeline", "gerar_atas"),
        ("licitasuite.motor.gerador", "gerar_atas"),
        ("licitasuite.geradores.pipeline", "Pipeline"),
        ("licitasuite.geradores.atas", "gerar_atas"),
    ]
    errors = []
    for module_name, attr_name in candidates:
        try:
            module = importlib.import_module(module_name)
            attr = getattr(module, attr_name)
            return module_name, attr_name, attr
        except Exception as exc:
            errors.append(f"{module_name}.{attr_name}: {exc}")
    raise RuntimeError("Não foi possível localizar o motor do LicitaSuite.\n\n" + "\n".join(errors))


def run_engine(zip_path: Path):
    module_name, attr_name, engine = find_engine()
    if attr_name == "Pipeline":
        pipeline = engine()
        for method_name in ["run", "execute", "process", "gerar"]:
            if hasattr(pipeline, method_name):
                return getattr(pipeline, method_name)(str(zip_path))
        raise RuntimeError(f"Pipeline encontrado em {module_name}, mas não possui método run/execute/process/gerar.")
    return engine(str(zip_path))


def make_result_zip():
    final_zip = OUTPUT_DIR / "atas_geradas_web.zip"
    if final_zip.exists():
        final_zip.unlink()
    with zipfile.ZipFile(final_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for file in ATAS_DIR.rglob("*"):
            if file.is_file():
                z.write(file, file.relative_to(ATAS_DIR))
    return final_zip


def main():
    ensure_dirs()
    st.markdown(
        '''
        <style>
        .title {text-align:center;color:#1f5494;font-size:40px;font-weight:800;margin-bottom:0;}
        .subtitle {text-align:center;color:#334155;font-size:19px;margin-top:0;margin-bottom:30px;}
        .footer {text-align:center;color:#64748b;font-size:13px;margin-top:35px;}
        </style>
        ''',
        unsafe_allow_html=True,
    )
    st.markdown("<div class='title'>LicitaSuite Web 1.0</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Gerador de Atas de Registro de Preços</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### 📂 Enviar processo")
        uploaded = st.file_uploader(
            "Selecione o ZIP do processo",
            type=["zip"],
            help="O ZIP deve conter modelo da Ata, Apêndice e PDF dos vencedores.",
        )
    with col2:
        st.markdown("### ℹ️ Status")
        st.info("Versão Web 1.0 Free")
        st.caption("Usa o motor da versão desktop.")

    st.divider()

    if uploaded is None:
        st.warning("Envie o ZIP do processo para iniciar.")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = UPLOAD_DIR / f"processo_{timestamp}.zip"
        with open(zip_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success(f"Arquivo recebido: {uploaded.name}")

        if st.button("⚙️ GERAR ATAS", type="primary", use_container_width=True):
            progress = st.progress(0, text="Preparando processamento...")
            try:
                clear_previous_outputs()
                progress.progress(20, text="Localizando motor do LicitaSuite...")
                module_name, attr_name, _ = find_engine()
                st.write(f"✓ Motor localizado: `{module_name}.{attr_name}`")

                progress.progress(45, text="Gerando atas...")
                st.write("✓ Processando documentos")
                run_engine(zip_path)

                progress.progress(80, text="Compactando resultado...")
                generated = sorted(ATAS_DIR.glob("*.docx"))
                if not generated:
                    progress.progress(0, text="Nenhuma ata encontrada")
                    st.error("O motor terminou, mas nenhuma Ata DOCX foi localizada em output/atas_geradas.")
                    return

                final_zip = make_result_zip()
                progress.progress(100, text="Concluído")
                st.success(f"✔ Processo concluído. {len(generated)} ata(s) gerada(s).")

                st.markdown("### 📄 Atas geradas")
                for doc in generated:
                    st.write(f"• {doc.name}")
                with open(final_zip, "rb") as f:
                    st.download_button(
                        "⬇️ BAIXAR ZIP COM AS ATAS",
                        data=f,
                        file_name="atas_geradas.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )
            except Exception as exc:
                progress.progress(0, text="Erro")
                st.error("Ocorreu um erro durante a geração.")
                st.exception(exc)

    st.markdown("<div class='footer'>LicitaSuite Web 1.0 Free • Engine LTS • © 2026</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()