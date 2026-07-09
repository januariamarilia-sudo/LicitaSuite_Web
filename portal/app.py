from __future__ import annotations

from datetime import datetime
from importlib import import_module
from pathlib import Path
import sys

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"
UPLOAD_DIR = ROOT_DIR / "portal_data" / "uploads"

PAGES = {
    "Visão geral": ("▦", "Acompanhe a operação em um só lugar"),
    "Processos": ("◫", "Organize processos e documentos"),
    "Gerar atas": ("✦", "Use o motor homologado da versão 4.0 LTS"),
    "Fornecedores": ("◎", "Consulte e mantenha o cadastro"),
    "Relatórios": ("▥", "Visualize indicadores e conferências"),
    "Configurações": ("⚙", "Personalize o novo ambiente"),
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --navy: #112647;
            --blue: #175cd3;
            --blue-soft: #eef4ff;
            --purple: #6941c6;
            --green: #067647;
            --amber: #b54708;
            --surface: #ffffff;
            --canvas: #f5f7fb;
            --border: #e4e7ec;
            --text: #101828;
            --muted: #667085;
        }
        .stApp { background: var(--canvas); color: var(--text); }
        header[data-testid="stHeader"] { background: transparent; }
        .block-container { max-width: 1280px; padding: 1.6rem 2.1rem 3rem; }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #102a53 0%, #0b1f3d 100%);
            border-right: 0;
            min-width: 270px;
        }
        section[data-testid="stSidebar"] > div { padding-top: 1.2rem; }
        section[data-testid="stSidebar"] [data-testid="stImage"] img {
            background: white;
            border-radius: 12px;
            padding: 10px;
        }
        section[data-testid="stSidebar"] .stRadio label {
            color: rgba(255,255,255,.72) !important;
            padding: .62rem .78rem;
            border-radius: 10px;
            font-weight: 650;
        }
        section[data-testid="stSidebar"] .stRadio label:hover {
            color: white !important;
            background: rgba(255,255,255,.08);
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: rgba(255,255,255,.74);
        }
        .ls-brand {
            padding: 1rem .2rem 1.3rem;
            border-bottom: 1px solid rgba(255,255,255,.12);
            margin-bottom: .9rem;
            position: relative;
        }
        .ls-brand:before {
            content: "";
            display: block;
            width: 74px;
            height: 4px;
            margin-bottom: 1rem;
            border-radius: 999px;
            background: linear-gradient(90deg, #ffffff 0 48%, #ec174c 48% 66%, #8b5cf6 66%);
        }
        .ls-brand-name {
            color: white;
            font-size: 1.34rem;
            font-weight: 800;
            letter-spacing: -.02em;
        }
        .ls-brand-version { color: #b2ccff; font-size: .78rem; margin-top: .2rem; }
        .ls-topbar {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1.5rem;
            margin-bottom: 1.45rem;
        }
        .ls-eyebrow {
            color: var(--blue);
            text-transform: uppercase;
            letter-spacing: .11em;
            font-size: .72rem;
            font-weight: 800;
            margin-bottom: .38rem;
        }
        .ls-title { color: var(--navy); font-size: 2rem; line-height: 1.1; font-weight: 800; }
        .ls-title:after {
            content: "";
            display: block;
            width: 46px;
            height: 3px;
            margin-top: .7rem;
            border-radius: 999px;
            background: linear-gradient(90deg, #175cd3, #6941c6, #ec174c);
        }
        .ls-subtitle { color: var(--muted); margin-top: .42rem; }
        .ls-env {
            border: 1px solid #abefc6;
            background: #ecfdf3;
            color: var(--green);
            padding: .48rem .78rem;
            border-radius: 999px;
            font-size: .78rem;
            font-weight: 750;
            white-space: nowrap;
        }
        .ls-kpi, .ls-panel, .ls-module, .ls-process {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: 0 1px 2px rgba(16,24,40,.04);
        }
        .ls-kpi { padding: 1.15rem 1.2rem; min-height: 126px; }
        .ls-kpi-icon {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: grid;
            place-items: center;
            background: var(--blue-soft);
            color: var(--blue);
            font-weight: 900;
            margin-bottom: .75rem;
        }
        .ls-kpi-label { color: var(--muted); font-size: .82rem; font-weight: 650; }
        .ls-kpi-value { color: var(--navy); font-size: 1.65rem; font-weight: 800; margin-top: .12rem; }
        .ls-kpi-note { color: var(--green); font-size: .72rem; margin-top: .16rem; }
        .ls-panel { padding: 1.3rem; margin-top: 1.2rem; }
        .ls-panel-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        .ls-panel-title { color: var(--navy); font-size: 1rem; font-weight: 800; }
        .ls-panel-note { color: var(--muted); font-size: .78rem; }
        .ls-process {
            padding: 1rem 1.05rem;
            margin-bottom: .7rem;
            display: grid;
            grid-template-columns: 1.1fr 2fr .85fr .8fr;
            gap: 1rem;
            align-items: center;
        }
        .ls-process-number { color: var(--navy); font-weight: 800; }
        .ls-process-object { color: var(--muted); font-size: .83rem; }
        .ls-badge {
            display: inline-block;
            padding: .28rem .58rem;
            border-radius: 999px;
            background: var(--blue-soft);
            color: var(--blue);
            font-size: .72rem;
            font-weight: 750;
            text-align: center;
        }
        .ls-module { padding: 1.2rem; min-height: 154px; }
        .ls-module-soon { color: var(--purple); font-size: .7rem; font-weight: 800; text-transform: uppercase; }
        .ls-module-title { color: var(--navy); font-weight: 800; margin: .75rem 0 .32rem; }
        .ls-module-text { color: var(--muted); font-size: .82rem; line-height: 1.5; }
        div[data-testid="stFileUploader"] section {
            background: #f8faff;
            border: 1.5px dashed #b2ccff;
            border-radius: 14px;
            padding: 1.2rem;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 10px;
            min-height: 42px;
            font-weight: 750;
        }
        .stButton > button[kind="primary"] {
            background: var(--blue);
            border-color: var(--blue);
        }
        @media(max-width: 900px) {
            .block-container { padding: 1rem; }
            .ls-topbar { flex-direction: column; }
            .ls-process { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    if "portal_processes" not in st.session_state:
        st.session_state.portal_processes = [
            {
                "number": "PL 49/2026",
                "object": "Registro de preços para aquisição de materiais",
                "status": "Atas geradas",
                "updated": "Hoje, 09:42",
            },
            {
                "number": "PL 48/2026",
                "object": "Aquisição compartilhada de medicamentos",
                "status": "Em conferência",
                "updated": "Ontem, 16:18",
            },
            {
                "number": "PL 45/2026",
                "object": "Processo homologado de referência",
                "status": "Concluído",
                "updated": "04/07/2026",
            },
        ]


def sidebar_navigation() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="ls-brand">
                <div class="ls-brand-name">Licita Suite-JM.adm</div>
                <div class="ls-brand-version">Gestão operacional • Ambiente 4.1</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        selected = st.radio(
            "Navegação",
            list(PAGES),
            format_func=lambda page: f"{PAGES[page][0]}  {page}",
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.caption("Motor de atas: 4.0 LTS • Build v2.2")
        st.caption("Ambiente independente do site atual")
    return selected


def render_topbar(page: str) -> None:
    _, subtitle = PAGES[page]
    st.markdown(
        f"""
        <div class="ls-topbar">
            <div>
                <div class="ls-eyebrow">Licita Suite-JM.adm</div>
                <div class="ls-title">{page}</div>
                <div class="ls-subtitle">{subtitle}</div>
            </div>
            <div class="ls-env">● Ambiente de evolução</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_process_card(process: dict) -> None:
    st.markdown(
        f"""
        <div class="ls-process">
            <div class="ls-process-number">{process['number']}</div>
            <div class="ls-process-object">{process['object']}</div>
            <div><span class="ls-badge">{process['status']}</span></div>
            <div class="ls-process-object">{process['updated']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    cols = st.columns(4)
    metrics = [
        ("◫", "Processos ativos", "3", "+1 nesta semana"),
        ("✦", "Atas geradas", "52", "Motor homologado"),
        ("◎", "Fornecedores", "24", "Banco integrado"),
        ("!", "Pendências", "2", "Requer conferência"),
    ]
    for col, (icon, label, value, note) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="ls-kpi">
                    <div class="ls-kpi-icon">{icon}</div>
                    <div class="ls-kpi-label">{label}</div>
                    <div class="ls-kpi-value">{value}</div>
                    <div class="ls-kpi-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="ls-panel">
            <div class="ls-panel-head">
                <div>
                    <div class="ls-panel-title">Processos recentes</div>
                    <div class="ls-panel-note">Últimas movimentações registradas no novo ambiente</div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )
    for process in st.session_state.portal_processes:
        render_process_card(process)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### Próximos módulos")
    module_cols = st.columns(3)
    modules = [
        ("Habilitação", "Checklist e conferência de documentos dos fornecedores."),
        ("Contratos", "Controle de instrumentos, vigências, saldos e responsáveis."),
        ("Publicações", "Agenda e histórico de publicações e atos oficiais."),
    ]
    for col, (title, text) in zip(module_cols, modules):
        with col:
            st.markdown(
                f"""
                <div class="ls-module">
                    <div class="ls-module-soon">Preparado para evolução</div>
                    <div class="ls-module-title">{title}</div>
                    <div class="ls-module-text">{text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_processes() -> None:
    with st.expander("Cadastrar novo processo", expanded=False):
        with st.form("new_process"):
            col1, col2 = st.columns(2)
            number = col1.text_input("Número do processo", placeholder="Ex.: PL 53/2026")
            status = col2.selectbox(
                "Situação inicial",
                ["Em criação", "Arquivos recebidos", "Em processamento"],
            )
            object_description = st.text_area(
                "Objeto",
                placeholder="Informe uma descrição curta do objeto da contratação.",
            )
            submitted = st.form_submit_button("Criar processo", type="primary")
            if submitted:
                if number.strip() and object_description.strip():
                    st.session_state.portal_processes.insert(
                        0,
                        {
                            "number": number.strip(),
                            "object": object_description.strip(),
                            "status": status,
                            "updated": datetime.now().strftime("%d/%m/%Y, %H:%M"),
                        },
                    )
                    st.success("Processo criado no novo ambiente.")
                    st.rerun()
                else:
                    st.warning("Informe o número e o objeto do processo.")

    search = st.text_input("Pesquisar processos", placeholder="Número, objeto ou situação")
    normalized = search.casefold().strip()
    processes = [
        process
        for process in st.session_state.portal_processes
        if not normalized
        or normalized
        in " ".join(
            [process["number"], process["object"], process["status"]]
        ).casefold()
    ]

    st.markdown(
        f'<div class="ls-panel-title">{len(processes)} processo(s) encontrado(s)</div>',
        unsafe_allow_html=True,
    )
    for process in processes:
        render_process_card(process)


def legacy_app_module():
    for path in (ROOT_DIR, WEB_DIR):
        path_string = str(path)
        if path_string not in sys.path:
            sys.path.insert(0, path_string)
    return import_module("web.app")


def render_ata_generator() -> None:
    st.info(
        "Este módulo utiliza o motor homologado da LicitaSuite Web 4.0 LTS "
        "(Build v2.2). A nova interface não altera as regras de geração."
    )

    with st.container(border=True):
        st.markdown("### Enviar processo")
        st.caption(
            "Selecione o ZIP contendo o modelo da ata, apêndice, PDF de vencedores "
            "e banco de fornecedores, quando aplicável."
        )
        uploaded_file = st.file_uploader(
            "Arquivo do processo",
            type=["zip"],
            help="O processamento ocorre localmente no ambiente da aplicação.",
        )
        generate = st.button(
            "Iniciar geração de atas",
            type="primary",
            use_container_width=True,
            disabled=uploaded_file is None,
        )

    if uploaded_file is None or not generate:
        return

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = UPLOAD_DIR / uploaded_file.name
    zip_path.write_bytes(uploaded_file.getbuffer())

    progress = st.progress(10, text="Preparando o processo...")
    try:
        legacy = legacy_app_module()
        module_name, attr_name, engine = legacy.find_engine()
        progress.progress(30, text="Motor homologado localizado.")

        result = legacy.run_engine(engine, zip_path)
        progress.progress(75, text="Conferindo arquivos gerados...")

        files = legacy.collect_generated_docx()
        if not files:
            st.error("O processamento terminou, mas nenhuma ata DOCX foi localizada.")
            return

        final_zip = legacy.make_download_zip(files)
        progress.progress(100, text="Geração concluída.")
        st.success(f"{len(files)} ata(s) gerada(s) por {module_name}.{attr_name}.")
        with final_zip.open("rb") as generated_file:
            st.download_button(
                "Baixar atas geradas",
                data=generated_file,
                file_name="atas_geradas.zip",
                mime="application/zip",
                use_container_width=True,
            )
        if hasattr(result, "errors") and result.errors:
            with st.expander("Avisos da geração"):
                for error in result.errors:
                    st.warning(str(error))
    except Exception as exc:
        progress.empty()
        st.error("Não foi possível concluir a geração neste processo.")
        st.exception(exc)


def render_suppliers() -> None:
    st.markdown(
        """
        <div class="ls-panel">
            <div class="ls-panel-title">Banco de fornecedores</div>
            <div class="ls-panel-note">
                Esta área receberá consulta, atualização e validação de CNPJ, endereço,
                representante, CPF, RG e órgão expedidor.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.text_input("Pesquisar fornecedor", placeholder="Razão social ou CNPJ")
    st.info("Módulo preparado para a próxima etapa de desenvolvimento.")


def render_reports() -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Processos concluídos", "1")
    col2.metric("Taxa sem divergências", "96%")
    col3.metric("Atas no período", "52")
    st.markdown(
        """
        <div class="ls-panel">
            <div class="ls-panel-title">Relatórios operacionais</div>
            <div class="ls-panel-note">
                Espaço reservado para conferência financeira, produtividade,
                pendências e histórico de versões.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_settings() -> None:
    with st.container(border=True):
        st.markdown("### Identidade do novo ambiente")
        st.text_input("Nome da aplicação", value="Licita Suite-JM.adm")
        st.text_input("Organização", value="JM.adm")
        st.selectbox("Ambiente", ["Evolução", "Homologação", "Produção"])
        st.toggle("Exibir módulos em desenvolvimento", value=True)
        st.button("Salvar preferências", type="primary")


def main() -> None:
    st.set_page_config(
        page_title="Licita Suite-JM.adm",
        page_icon="📑",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    initialize_state()
    selected_page = sidebar_navigation()
    render_topbar(selected_page)

    renderers = {
        "Visão geral": render_dashboard,
        "Processos": render_processes,
        "Gerar atas": render_ata_generator,
        "Fornecedores": render_suppliers,
        "Relatórios": render_reports,
        "Configurações": render_settings,
    }
    renderers[selected_page]()


if __name__ == "__main__":
    main()
