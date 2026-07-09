from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR_STRING = str(ROOT_DIR)
if ROOT_DIR_STRING not in sys.path:
    sys.path.insert(0, ROOT_DIR_STRING)

from portal.process_store import (
    PROCESS_STATUSES,
    create_process,
    format_timestamp,
    process_metrics,
    record_generation,
    search_processes,
    update_technical_qualification,
    update_process_status,
)
from portal.foco_docs import (
    PROFILE_CHECKLISTS,
    analyze_document_zip,
    build_organized_zip,
    build_print_pdf,
    get_selected_pdf_documents,
    supplier_label_from_package,
)
from portal.portal_compras import (
    PORTAL_PARTNERS_URL,
    build_process_search_url,
)


WEB_DIR = ROOT_DIR / "web"
UPLOAD_DIR = ROOT_DIR / "portal_data" / "uploads"

PAGES = {
    "Visão geral": ("▦", "Acompanhe a operação em um só lugar"),
    "Processos": ("◫", "Organize processos e documentos"),
    "FOCO DOCS": ("◇", "Classifique e organize documentos em um clique"),
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
        st.session_state.portal_processes = []


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
            <div class="ls-process-object">{format_timestamp(process['updated_at'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    metrics_data = process_metrics(st.session_state.portal_processes)
    cols = st.columns(4)
    metrics = [
        ("◫", "Processos ativos", str(metrics_data["active"]), "Em acompanhamento"),
        ("✦", "Atas geradas", str(metrics_data["atas"]), "Motor homologado"),
        ("◎", "Fornecedores", str(metrics_data["suppliers"]), "Processados"),
        ("!", "Pendências", str(metrics_data["pending"]), "Requer conferência"),
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
    if st.session_state.portal_processes:
        for process in st.session_state.portal_processes[:5]:
            render_process_card(process)
    else:
        st.info(
            "Nenhum processo cadastrado. Abra o módulo Processos para iniciar "
            "o primeiro workspace operacional."
        )
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
    with st.expander(
        "Cadastrar novo processo",
        expanded=not bool(st.session_state.portal_processes),
    ):
        with st.form("new_process"):
            col1, col2 = st.columns(2)
            number = col1.text_input("Número do processo", placeholder="Ex.: PL 53/2026")
            modality = col2.text_input(
                "Modalidade",
                placeholder="Ex.: Pregão Eletrônico",
            )
            object_description = st.text_area(
                "Objeto",
                placeholder="Informe uma descrição curta do objeto da contratação.",
            )
            technical_qualification = st.text_area(
                "Qualificação técnica exigida (opcional)",
                placeholder=(
                    "Descreva as licenças, autorizações, registros, atestados, "
                    "certificados e demais exigências técnicas deste processo."
                ),
                help=(
                    "Este texto será usado como referência na separação e na "
                    "conferência dos documentos dos fornecedores."
                ),
            )
            col3, col4 = st.columns(2)
            responsible = col3.text_input("Responsável", placeholder="Nome do responsável")
            observations = col4.text_input(
                "Observações iniciais",
                placeholder="Informação opcional",
            )
            submitted = st.form_submit_button("Criar processo", type="primary")
            if submitted:
                if number.strip() and modality.strip() and object_description.strip():
                    st.session_state.portal_processes.insert(
                        0,
                        create_process(
                            number,
                            modality,
                            object_description,
                            responsible,
                            observations,
                            technical_qualification,
                        ),
                    )
                    st.success("Processo criado no novo ambiente.")
                    st.rerun()
                else:
                    st.warning("Informe o número, a modalidade e o objeto do processo.")

    search = st.text_input("Pesquisar processos", placeholder="Número, objeto ou situação")
    processes = search_processes(st.session_state.portal_processes, search)

    st.markdown(
        f'<div class="ls-panel-title">{len(processes)} processo(s) encontrado(s)</div>',
        unsafe_allow_html=True,
    )
    for process in processes:
        render_process_card(process)
        with st.expander(f"Acompanhar {process['number']}"):
            st.caption(
                f"{process['modality']} • Responsável: "
                f"{process.get('responsible') or 'Não informado'}"
            )
            metric_cols = st.columns(4)
            metric_cols[0].metric("Fornecedores", process.get("suppliers", 0))
            metric_cols[1].metric("Itens", process.get("items", 0))
            metric_cols[2].metric("Atas", process.get("atas", 0))
            metric_cols[3].metric("Pendências", process.get("pending", 0))

            status = st.selectbox(
                "Situação",
                PROCESS_STATUSES,
                index=PROCESS_STATUSES.index(process["status"]),
                key=f"status_{process['id']}",
            )
            if st.button("Atualizar situação", key=f"update_{process['id']}"):
                update_process_status(process, status)
                st.success("Situação atualizada.")
                st.rerun()

            technical_qualification = st.text_area(
                "Qualificação técnica exigida (opcional)",
                value=process.get("technical_qualification", ""),
                placeholder="Descreva as exigências técnicas previstas no edital.",
                key=f"technical_qualification_{process['id']}",
            )
            if st.button(
                "Salvar qualificação técnica",
                key=f"save_technical_qualification_{process['id']}",
            ):
                update_technical_qualification(process, technical_qualification)
                st.success("Qualificação técnica salva para este processo.")
                st.rerun()

            if process.get("observations"):
                st.markdown(f"**Observações:** {process['observations']}")

            st.markdown("**Histórico recente**")
            for event in reversed(process.get("history", [])[-5:]):
                st.caption(
                    f"{format_timestamp(event['created_at'])} — "
                    f"{event['title']}: {event['description']}"
                )


def legacy_app_module():
    for path in (ROOT_DIR, WEB_DIR):
        path_string = str(path)
        if path_string not in sys.path:
            sys.path.insert(0, path_string)
    return import_module("web.app")


def render_foco_docs() -> None:
    st.info(
        "O FOCO DOCS organiza a documentação de fornecedores sem alterar "
        "os arquivos originais enviados."
    )
    with st.expander("Buscar documentos no Portal de Compras Públicas", expanded=True):
        portal_col1, portal_col2 = st.columns(2)
        process_number = portal_col1.text_input(
            "Número do pregão",
            placeholder="Ex.: 39/2026",
            key="portal_process_number",
        )
        agency = portal_col2.text_input(
            "Órgão comprador",
            value="ICISMEP",
            key="portal_agency",
        )
        search_url = build_process_search_url(process_number, agency)
        st.link_button(
            "Localizar processo e documentos no Portal",
            search_url,
            use_container_width=True,
            disabled=not process_number.strip(),
        )
        st.caption(
            "A busca já abre filtrada pelo pregão e pelo órgão. O Portal oferece "
            "integração direta por API para compradores e parceiros; o conector "
            "automático será habilitado quando a credencial oficial estiver disponível."
        )
        st.link_button(
            "Solicitar integração oficial do Portal",
            PORTAL_PARTNERS_URL,
            use_container_width=True,
        )

    st.markdown("### Organizar e renomear documentos dos fornecedores")
    st.caption(
        "Envie um ZIP contendo uma pasta para cada fornecedor. O sistema extrai "
        "todos os arquivos, renomeia os documentos reconhecidos pelo item do edital "
        "e preserva os demais em uma pasta separada."
    )
    process_options = {
        process["id"]: f"{process['number']} — {process['object']}"
        for process in st.session_state.portal_processes
    }
    selected_process = None
    if process_options:
        selected_process_id = st.selectbox(
            "Processo da conferência",
            list(process_options),
            format_func=process_options.get,
            key="foco_docs_process",
        )
        selected_process = next(
            process
            for process in st.session_state.portal_processes
            if process["id"] == selected_process_id
        )
        technical_qualification = selected_process.get(
            "technical_qualification", ""
        )
        if technical_qualification:
            st.markdown("**Qualificação técnica exigida neste processo:**")
            st.info(technical_qualification)
        else:
            st.caption(
                "Qualificação técnica não informada — este campo é opcional e "
                "não impede a separação dos documentos."
            )
    else:
        technical_qualification = ""
        st.caption(
            "A vinculação a um processo é opcional para organizar este pacote."
        )

    technical_qualification = st.text_area(
        "Qualificação técnica deste pregão (opcional)",
        value=technical_qualification,
        placeholder=(
            "Ex.: exigir Alvará/Licença Sanitária, AFE ANVISA, Registro ANVISA "
            "e Certificado de Regularidade."
        ),
        help=(
            "Os documentos 10.9 só serão cobrados quando forem descritos aqui. "
            "A parte geral 7.0, 7.1, 7.2 e 7.3 vale para todos."
        ),
        key=(
            f"foco_docs_technical_"
            f"{selected_process['id'] if selected_process else 'sem_processo'}"
        ),
    )
    profile = "Padrão geral"
    st.caption(
        "Conferência padrão: documentos 7.0, 7.1, 7.2 e 7.3. "
        "Qualificação técnica 10.9: somente quando informada acima."
    )
    upload_col1, upload_col2 = st.columns(2)
    uploaded_zip = upload_col1.file_uploader(
        "1. Pacote com as pastas dos fornecedores",
        type=["zip", "rar", "tar", "tgz", "gz"],
        key="foco_docs_upload",
        help="Dentro do ZIP, mantenha uma pasta com o nome de cada fornecedor.",
    )
    winners_report = upload_col2.file_uploader(
        "2. Relatório PDF de itens vencidos (opcional)",
        type=["pdf"],
        key="foco_docs_winners_report",
        help=(
            "O relatório será incluído no pacote como referência para a "
            "conferência dos catálogos e registros dos produtos."
        ),
    )
    process = st.button(
        "Separar e renomear todos os documentos",
        type="primary",
        use_container_width=True,
        disabled=uploaded_zip is None,
    )

    if process and uploaded_zip is not None:
        progress = st.progress(15, text="Lendo o pacote documental...")
        try:
            source_bytes = uploaded_zip.getvalue()
            reference_file = (
                (winners_report.name, winners_report.getvalue())
                if winners_report is not None
                else None
            )
            analysis = analyze_document_zip(
                source_bytes,
                profile,
                technical_qualification,
                reference_file,
                supplier_label_from_package(uploaded_zip.name),
                uploaded_zip.name,
            )
            progress.progress(
                70,
                text="Separando fornecedores e renomeando documentos...",
            )
            organized_zip = build_organized_zip(
                source_bytes,
                analysis,
                reference_file,
            )
            st.session_state.foco_docs_result = {
                "analysis": analysis,
                "zip": organized_zip,
                "source_bytes": source_bytes,
                "source_name": uploaded_zip.name,
                "process_id": selected_process["id"] if selected_process else None,
                "winners_report": (
                    winners_report.name if winners_report is not None else None
                ),
            }
            st.session_state.pop("foco_docs_print_result", None)
            for group_index in range(7):
                st.session_state.pop(
                    f"foco_docs_print_selection_{group_index}",
                    None,
                )
            progress.progress(100, text="Organização concluída.")
        except ValueError as exc:
            progress.empty()
            st.error(str(exc))

    result = st.session_state.get("foco_docs_result")
    if not result:
        st.caption(
            "Você receberá um único ZIP. Dentro dele, cada fornecedor terá a pasta "
            "'01 - Documentos Exigidos', a pasta '02 - Documentos Não Utilizados', "
            "a pasta '03 - Documentos Não Identificados' e seu relatório."
        )
        return

    analysis = result["analysis"]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Documentos", len(analysis["documents"]))
    metric_cols[1].metric("Básicos", analysis["totals"]["BÁSICOS"])
    metric_cols[2].metric("Técnicos", analysis["totals"]["TÉCNICOS"])
    metric_cols[3].metric(
        "Não identificados",
        analysis["totals"]["NÃO CLASSIFICADOS"],
    )
    st.caption(
        f"{len(analysis.get('suppliers', []))} fornecedor(es) localizado(s) no pacote."
    )

    if analysis["ocr_candidates"] and not analysis.get("ocr_processed"):
        st.warning(
            f"{analysis['ocr_candidates']} imagem(ns) marcada(s) como candidata(s) "
            "a OCR, mas sem texto reconhecido."
        )
    if analysis.get("ocr_processed"):
        st.success(
            f"OCR aplicado em {analysis['ocr_processed']} documento(s) escaneado(s)."
        )

    tab_checklist, tab_validation, tab_documents = st.tabs(
        ["Checklist", "Conferência / validação", "Documentos"]
    )
    with tab_checklist:
        st.dataframe(analysis["checklist"], use_container_width=True, hide_index=True)
    with tab_validation:
        validation_codes = {
            "7.0.1",
            "7.2.1",
            "7.2.2",
            "7.2.3",
            "7.2.4",
            "7.2.5",
            "7.2.6",
            "7.3.1",
        }
        validation_rows = [
            {
                "Fornecedor": document["supplier"],
                "Documento": document["standardized_name"],
                "Grupo": document["document_group"],
                "Validade": document["validity_date"] or "-",
                "Situação": document["validity_status"],
                "Validar no site oficial": document["validation_url"] or None,
                "Orientação": document["validation_note"],
            }
            for document in analysis["documents"]
            if document["selected_for_requirement"]
            and document["document_code"] in validation_codes
        ]
        if not validation_rows:
            st.info(
                "Nenhum documento obrigatório de validação foi localizado "
                "neste pacote."
            )
        else:
            valid_count = sum(row["Situação"] == "Válido" for row in validation_rows)
            expired_count = sum(row["Situação"] == "Vencido" for row in validation_rows)
            pending_count = sum(
                row["Situação"] == "Não identificada" for row in validation_rows
            )
            col_valid, col_expired, col_pending = st.columns(3)
            col_valid.metric("Válidos", valid_count)
            col_expired.metric("Vencidos", expired_count)
            col_pending.metric("Sem validade lida", pending_count)
            st.caption(
                "Use esta aba para conferir SICAF, CNPJ, Federal, Estadual, "
                "Municipal, FGTS, Trabalhista e Falência."
            )
            st.dataframe(
                validation_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Validar no site oficial": st.column_config.LinkColumn(
                        "Validar",
                        help="Abre o portal oficial ou o endereço localizado no documento.",
                        display_text="Abrir site oficial",
                    ),
                },
            )
            validation_report = "\n".join(
                [
                    "ROTEIRO DE CONFERÊNCIA E VALIDAÇÃO",
                    "",
                    *[
                        (
                            f"{row['Fornecedor']} | {row['Documento']} | "
                            f"Validade: {row['Validade']} | "
                            f"Situação: {row['Situação']} | "
                            f"Validação: "
                            f"{row['Validar no site oficial'] or row['Orientação']}"
                        )
                        for row in validation_rows
                    ],
                ]
            )
            st.download_button(
                "Baixar roteiro de validação",
                data=validation_report.encode("utf-8"),
                file_name="ROTEIRO_DE_VALIDACAO_DOCUMENTAL.txt",
                mime="text/plain",
                use_container_width=True,
            )
    with tab_documents:
        all_print_rows = [
            {
                    "Selecionar": False,
                    "ID": document["source"],
                    "Grupo": document["document_group"],
                    "Fornecedor": document["supplier"],
                    "Arquivo original": document["name"],
                    "Nome organizado": document["standardized_name"],
                    "Identificado": "Sim" if document["identified"] else "Não",
                    "Usado": (
                        "Sim" if document["selected_for_requirement"] else "Não"
                    ),
                    "Identificado por": document["identified_by"],
                    "Validade": document["validity_date"] or "-",
                    "Situação": document["validity_status"],
                    "Validar no site oficial": document["validation_url"] or None,
                    "Orientação": document["validation_note"],
                    "Categoria": document["category"],
                    "Extensão": document["extension"],
                    "Tamanho (KB)": round(document["size"] / 1024, 1),
                }
                for document in analysis["documents"]
                if document["extension"] == ".pdf"
        ]
        group_names = (
            "Documentos iniciais",
            "Habilitação jurídica",
            "Regularidade fiscal",
            "Regularidade trabalhista",
            "Qualificação econômico-financeira",
            "Qualificação técnica",
            "Outros documentos",
        )
        group_tabs = st.tabs(group_names)
        selected_sources = []
        for group_index, (group_name, group_tab) in enumerate(
            zip(group_names, group_tabs)
        ):
            with group_tab:
                group_rows = [
                    row for row in all_print_rows if row["Grupo"] == group_name
                ]
                if not group_rows:
                    st.caption("Nenhum documento localizado neste grupo.")
                    continue
                edited_documents = st.data_editor(
                    group_rows,
                    use_container_width=True,
                    hide_index=True,
                    disabled=[
                        column
                        for column in group_rows[0]
                        if column != "Selecionar"
                    ],
                    column_config={
                        "Selecionar": st.column_config.CheckboxColumn(
                            "Imprimir",
                            help=(
                                "Marque os documentos que deseja reunir "
                                "para impressão."
                            ),
                            default=False,
                        ),
                        "ID": None,
                        "Grupo": None,
                        "Validar no site oficial": st.column_config.LinkColumn(
                            "Validar",
                            help="Abre o portal oficial para conferência.",
                            display_text="Abrir site oficial",
                        ),
                    },
                    key=f"foco_docs_print_selection_{group_index}",
                )
                selected_sources.extend(
                    row["ID"]
                    for row in edited_documents
                    if row["Selecionar"]
                )
        st.caption(
            f"{len(selected_sources)} documento(s) selecionado(s) para impressão."
        )
        print_mode = st.radio(
            "Como deseja preparar?",
            ("Um único PDF", "Documentos separados"),
            horizontal=True,
            key="foco_docs_print_mode",
        )
        if st.button(
            "Preparar documentos selecionados para impressão",
            use_container_width=True,
            disabled=not selected_sources,
        ):
            try:
                if print_mode == "Um único PDF":
                    print_pdf, document_count, page_count = build_print_pdf(
                        result["source_bytes"],
                        analysis,
                        selected_sources,
                    )
                    st.session_state.foco_docs_print_result = {
                        "mode": "single",
                        "pdf": print_pdf,
                        "documents": document_count,
                        "pages": page_count,
                    }
                else:
                    individual_documents = get_selected_pdf_documents(
                        result["source_bytes"],
                        analysis,
                        selected_sources,
                    )
                    st.session_state.foco_docs_print_result = {
                        "mode": "individual",
                        "files": individual_documents,
                        "documents": len(individual_documents),
                    }
            except ValueError as exc:
                st.error(str(exc))

        print_result = st.session_state.get("foco_docs_print_result")
        if print_result and print_result["mode"] == "single":
            st.success(
                f"PDF preparado: {print_result['documents']} documento(s), "
                f"{print_result['pages']} página(s)."
            )
            st.download_button(
                "Baixar PDF selecionado para imprimir",
                data=print_result["pdf"],
                file_name="documentos_selecionados_para_impressao.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        elif print_result and print_result["mode"] == "individual":
            st.success(
                f"{print_result['documents']} documento(s) preparado(s) "
                "separadamente."
            )
            for index, document in enumerate(print_result["files"]):
                st.download_button(
                    f"Abrir/baixar — {document['name']}",
                    data=document["content"],
                    file_name=document["name"],
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"download_individual_{index}_{document['name']}",
                )

    st.download_button(
        "Baixar todos os fornecedores organizados",
        data=result["zip"],
        file_name="fornecedores_documentos_organizados.zip",
        mime="application/zip",
        use_container_width=True,
    )


def render_ata_generator() -> None:
    st.info(
        "Este módulo utiliza o motor homologado da LicitaSuite Web 4.0 LTS "
        "(Build v2.2). A nova interface não altera as regras de geração."
    )

    process_options = {
        process["id"]: f"{process['number']} — {process['object']}"
        for process in st.session_state.portal_processes
    }
    selected_process_id = None
    if process_options:
        selected_process_id = st.selectbox(
            "Vincular geração ao processo",
            list(process_options),
            format_func=process_options.get,
        )
    else:
        st.warning(
            "Cadastre um processo antes de gerar atas, para que o resultado fique "
            "registrado na Central de Processos."
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
            disabled=uploaded_file is None or selected_process_id is None,
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
        selected_process = next(
            process
            for process in st.session_state.portal_processes
            if process["id"] == selected_process_id
        )
        result_errors = getattr(result, "errors", []) or []
        record_generation(
            selected_process,
            atas=len(files),
            suppliers=getattr(result, "suppliers_count", len(files)),
            items=getattr(result, "items_count", 0),
            pending=len(result_errors),
            artifact=final_zip.name,
        )
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
        if result_errors:
            with st.expander("Avisos da geração"):
                for error in result_errors:
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
    metrics_data = process_metrics(st.session_state.portal_processes)
    col1, col2, col3 = st.columns(3)
    col1.metric("Processos concluídos", metrics_data["completed"])
    total_processes = len(st.session_state.portal_processes)
    clean_processes = sum(
        not process.get("pending", 0)
        for process in st.session_state.portal_processes
        if process.get("atas", 0)
    )
    processed = sum(
        bool(process.get("atas", 0)) for process in st.session_state.portal_processes
    )
    rate = round((clean_processes / processed) * 100) if processed else 0
    col2.metric("Taxa sem divergências", f"{rate}%")
    col3.metric("Atas processadas", metrics_data["atas"])
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
        "FOCO DOCS": render_foco_docs,
        "Gerar atas": render_ata_generator,
        "Fornecedores": render_suppliers,
        "Relatórios": render_reports,
        "Configurações": render_settings,
    }
    renderers[selected_page]()


if __name__ == "__main__":
    main()
