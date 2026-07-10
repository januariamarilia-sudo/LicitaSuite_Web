from __future__ import annotations

import os
from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR_STRING = str(ROOT_DIR)
if ROOT_DIR_STRING not in sys.path:
    sys.path.insert(0, ROOT_DIR_STRING)

from portal.foco_docs import (
    analyze_document_zip,
    build_organized_zip,
    build_print_pdf,
    get_selected_pdf_documents,
    supplier_label_from_package,
    tcu_validation_url,
)

PORTAL_API_SECRET_NAME = "PORTAL_COMPRAS_API_KEY"


def portal_api_configured() -> bool:
    try:
        secret_value = st.secrets.get(PORTAL_API_SECRET_NAME, "")
    except Exception:
        secret_value = ""
    return bool(secret_value or os.environ.get(PORTAL_API_SECRET_NAME, ""))


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #071a33;
            --navy: #0b2347;
            --navy-2: #12386f;
            --blue: #1d5fd1;
            --blue-soft: #eaf2ff;
            --gold: #c99a42;
            --gold-soft: #fff7e8;
            --green: #067647;
            --amber: #b54708;
            --canvas: #f5f7fb;
            --card: rgba(255,255,255,.88);
            --border: rgba(130,148,176,.30);
            --muted: #667085;
            --shadow: 0 24px 70px rgba(8, 30, 63, .12);
        }
        .stApp {
            background:
                radial-gradient(circle at 8% 5%, rgba(201,154,66,.22), transparent 24rem),
                radial-gradient(circle at 92% 0%, rgba(29,95,209,.18), transparent 25rem),
                linear-gradient(180deg, #fbfcff 0%, var(--canvas) 100%);
            color: var(--ink);
        }
        .block-container {
            max-width: 1240px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        section[data-testid="stSidebar"] {
            background:
                radial-gradient(circle at top, rgba(201,154,66,.28), transparent 14rem),
                linear-gradient(180deg, #071a33 0%, #102a55 100%);
        }
        section[data-testid="stSidebar"] * {
            color: #ffffff !important;
        }
        .foco-hero {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,.70);
            border-radius: 30px;
            padding: 2rem 2.15rem;
            background:
                linear-gradient(135deg, rgba(255,255,255,.96) 0%, rgba(244,248,255,.92) 54%, rgba(255,247,232,.82) 100%);
            box-shadow: var(--shadow);
            margin-bottom: 1.05rem;
        }
        .foco-hero:before {
            content: "";
            position: absolute;
            width: 18rem;
            height: 18rem;
            right: -7rem;
            top: -8rem;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(201,154,66,.36), transparent 65%);
        }
        .foco-hero:after {
            content: "";
            position: absolute;
            width: 22rem;
            height: 22rem;
            right: 5rem;
            bottom: -15rem;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(29,95,209,.16), transparent 64%);
        }
        .foco-eyebrow {
            position: relative;
            color: var(--blue);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin-bottom: .25rem;
        }
        .foco-title {
            position: relative;
            color: var(--navy);
            font-size: clamp(2.25rem, 4vw, 4.1rem);
            line-height: 1.05;
            font-weight: 900;
            margin: 0;
            letter-spacing: -.055em;
        }
        .foco-subtitle {
            position: relative;
            color: var(--muted);
            font-size: 1.03rem;
            margin-top: .6rem;
            max-width: 48rem;
            line-height: 1.65;
        }
        .foco-badges {
            position: relative;
            display: flex;
            gap: .55rem;
            flex-wrap: wrap;
            margin-top: 1.1rem;
        }
        .foco-badge {
            border: 1px solid rgba(29,95,209,.16);
            border-radius: 999px;
            background: rgba(255,255,255,.74);
            color: var(--navy);
            font-size: .78rem;
            font-weight: 800;
            padding: .42rem .72rem;
            box-shadow: 0 10px 25px rgba(16,33,63,.06);
        }
        .foco-card {
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.15rem 1.25rem;
            background: var(--card);
            box-shadow: 0 14px 45px rgba(8,30,63,.08);
            margin: 1rem 0;
        }
        .foco-section-title {
            color: var(--navy);
            font-size: 1.1rem;
            font-weight: 900;
            margin: 0 0 .25rem 0;
        }
        .foco-section-note {
            color: var(--muted);
            line-height: 1.55;
            margin-bottom: .8rem;
        }
        .foco-steps {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .85rem;
            margin: .9rem 0 1.1rem;
        }
        .foco-step {
            border: 1px solid rgba(130,148,176,.24);
            border-radius: 18px;
            background: rgba(255,255,255,.78);
            padding: .9rem .95rem;
        }
        .foco-step-number {
            color: var(--gold);
            font-weight: 900;
            font-size: .82rem;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .foco-step-title {
            color: var(--navy);
            font-weight: 850;
            margin-top: .25rem;
        }
        .foco-step-text {
            color: var(--muted);
            font-size: .84rem;
            line-height: 1.45;
            margin-top: .2rem;
        }
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 14px;
            font-weight: 750;
            min-height: 2.9rem;
            box-shadow: 0 10px 24px rgba(29,95,209,.14);
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--blue) 0%, var(--navy-2) 100%);
            border: 0;
        }
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,.92);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1rem 1.05rem;
            box-shadow: 0 12px 34px rgba(8,30,63,.07);
        }
        div[data-testid="stFileUploader"] {
            border: 1px dashed rgba(29,95,209,.32);
            border-radius: 20px;
            background: rgba(234,242,255,.46);
            padding: .45rem .75rem .75rem;
        }
        div[data-testid="stTabs"] button {
            font-weight: 800;
        }
        @media (max-width: 820px) {
            .foco-steps {
                grid-template-columns: 1fr;
            }
            .foco-hero {
                padding: 1.45rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="foco-hero">
            <div class="foco-eyebrow">Licita Suite-JM.adm</div>
            <h1 class="foco-title">FOCO DOCS</h1>
            <div class="foco-subtitle">
                Aplicativo exclusivo para separar, reconhecer, renomear e baixar
                documentos de fornecedores com agilidade, elegância e rastreio de conferência.
            </div>
            <div class="foco-badges">
                <span class="foco-badge">Modo rápido</span>
                <span class="foco-badge">Pastas por fornecedor</span>
                <span class="foco-badge">Validade essencial</span>
                <span class="foco-badge">Download organizado</span>
            </div>
        </div>
        <div class="foco-steps">
            <div class="foco-step">
                <div class="foco-step-number">Passo 01</div>
                <div class="foco-step-title">Enviar pacote</div>
                <div class="foco-step-text">Anexe o ZIP/RAR/TAR com os documentos dos fornecedores.</div>
            </div>
            <div class="foco-step">
                <div class="foco-step-number">Passo 02</div>
                <div class="foco-step-title">Separar e renomear</div>
                <div class="foco-step-text">O sistema identifica os documentos exigidos e organiza o restante.</div>
            </div>
            <div class="foco-step">
                <div class="foco-step-number">Passo 03</div>
                <div class="foco-step-title">Baixar pronto</div>
                <div class="foco-step-text">Receba um ZIP final com pastas, nomes padronizados e conferência.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def reset_print_selection() -> None:
    st.session_state.pop("foco_docs_print_result", None)
    for group_index in range(7):
        st.session_state.pop(f"foco_docs_print_selection_{group_index}", None)


def render_inputs() -> None:
    st.markdown(
        """
        <div class="foco-card">
            <div class="foco-section-title">1. Envie o pacote documental</div>
            <div class="foco-section-note">
                Use um ZIP/RAR/TAR com os documentos dos fornecedores. O modo padrão é
                rápido: prioriza o nome do arquivo, separa o que está na lista exigida
                e envia o restante para pastas de apoio.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Use um ZIP/RAR/TAR com os documentos dos fornecedores. O modo padrão é "
        "rápido: ele prioriza nome do arquivo, separa o que está na lista exigida "
        "e manda o restante para pastas de apoio."
    )

    technical_qualification = st.text_area(
        "Qualificação técnica deste pregão (opcional)",
        placeholder=(
            "Ex.: exigir Alvará/Licença Sanitária, AFE ANVISA, Registro ANVISA, "
            "Certificado de Regularidade ou Atestado de Capacidade Técnica."
        ),
        help=(
            "Preencha somente quando o edital exigir documentos técnicos. "
            "Se ficar em branco, o app foca nos documentos básicos de habilitação."
        ),
        key="foco_docs_technical",
    )

    session_date = st.date_input(
        "Data da sessão (opcional)",
        value=None,
        format="DD/MM/YYYY",
        help=(
            "Se preenchida, CNPJ/CNDs/FGTS/CNDT/Falência serão conferidos com "
            "esta data como referência."
        ),
        key="foco_docs_session_date",
    )

    with st.expander("Opções avançadas — use somente quando precisar", expanded=False):
        read_internal_validity = st.checkbox(
            "Buscar validade dentro dos PDFs quando não estiver no nome",
            value=False,
            help="Deixe desligado para máxima velocidade.",
            key="foco_docs_read_internal_validity",
        )
        split_compound_pdfs = st.checkbox(
            "Separar PDF único que contém vários documentos",
            value=False,
            help="Deixe desligado, exceto quando o fornecedor mandar tudo em um PDF só.",
            key="foco_docs_split_compound_pdfs",
        )

    upload_col1, upload_col2 = st.columns(2)
    uploaded_zip = upload_col1.file_uploader(
        "Pacote com documentos dos fornecedores",
        type=["zip", "rar", "tar", "tgz", "gz"],
        key="foco_docs_upload",
    )
    winners_report = upload_col2.file_uploader(
        "Documento do processo / vencedores (opcional)",
        type=["pdf"],
        key="foco_docs_winners_report",
        help=(
            "Pode ser Registro de Preço, relatório de vencedores ou documento "
            "com itens vencidos. Ele entra no início da pasta organizada."
        ),
    )

    process = st.button(
        "Separar e renomear documentos",
        type="primary",
        use_container_width=True,
        disabled=uploaded_zip is None,
    )

    if not process or uploaded_zip is None:
        return

    progress = st.progress(10, text="Lendo pacote documental...")
    try:
        source_bytes = uploaded_zip.getvalue()
        reference_file = (
            (winners_report.name, winners_report.getvalue())
            if winners_report is not None
            else None
        )
        analysis = analyze_document_zip(
            source_bytes,
            "Padrão geral",
            technical_qualification,
            reference_file,
            supplier_label_from_package(uploaded_zip.name),
            uploaded_zip.name,
            fast_mode=True,
            allow_ocr=False,
            split_compound_pdfs=split_compound_pdfs,
            read_internal_validity=read_internal_validity,
            session_date=session_date,
        )
        progress.progress(75, text="Montando ZIP organizado...")
        organized_zip = build_organized_zip(source_bytes, analysis, reference_file)
        st.session_state.foco_docs_result = {
            "analysis": analysis,
            "zip": organized_zip,
            "source_bytes": source_bytes,
            "source_name": uploaded_zip.name,
            "winners_report": winners_report.name if winners_report is not None else None,
        }
        reset_print_selection()
        progress.progress(100, text="Organização concluída.")
    except Exception as exc:
        progress.empty()
        st.error("Não consegui processar este pacote.")
        st.info(
            "Se o arquivo for muito grande, tente enviar um ZIP menor ou deixe as "
            "opções avançadas desligadas."
        )
        with st.expander("Detalhes do erro"):
            st.code(f"{type(exc).__name__}: {exc}")


def validation_rows(analysis: dict) -> list[dict]:
    validation_codes = {
        "10.7.1",
        "10.7.2",
        "10.7.3",
        "10.7.4",
        "10.7.5",
        "10.7.6",
        "10.8.1",
    }
    rows = [
        {
            "Fornecedor": document["supplier"],
            "Documento": document["standardized_name"],
            "Grupo": document["document_group"],
            "Validade": document["validity_date"] or "-",
            "Situação": document["validity_status"],
            "Validar no site oficial": document["validation_url"] or None,
            "Dados para consulta": document.get("validation_data", ""),
            "Orientação": document["validation_note"],
        }
        for document in analysis["documents"]
        if document["selected_for_requirement"]
        and document["document_code"] in validation_codes
    ]
    for supplier in analysis.get("suppliers", []) or ["Fornecedor não identificado"]:
        supplier_cnpj = analysis.get("supplier_cnpjs", {}).get(supplier, "")
        rows.append(
            {
                "Fornecedor": supplier,
                "Documento": "10.5 - Consulta Consolidada TCU / CEIS-CNEP",
                "Grupo": "Consulta de impedimentos",
                "Validade": "-",
                "Situação": "A conferir",
                "Validar no site oficial": tcu_validation_url(supplier_cnpj or supplier),
                "Dados para consulta": supplier_cnpj or "",
                "Orientação": "Consultar TCU/APF e CEIS/CNEP.",
            }
        )
    return rows


def render_validation_tab(analysis: dict) -> None:
    rows = validation_rows(analysis)
    if not rows:
        st.info("Nenhum documento de validação foi localizado neste pacote.")
        return

    valid_count = sum(row["Situação"] == "Válido" for row in rows)
    expired_count = sum(row["Situação"] == "Vencido" for row in rows)
    pending_count = sum(row["Situação"] == "Não identificada" for row in rows)
    review_count = sum(row["Situação"] == "A conferir" for row in rows)
    col_valid, col_expired, col_pending, col_review = st.columns(4)
    col_valid.metric("Válidos", valid_count)
    col_expired.metric("Vencidos", expired_count)
    col_pending.metric("Sem validade lida", pending_count)
    col_review.metric("A conferir", review_count)

    st.caption(
        "Validade restrita a CNPJ, Federal, Estadual, Municipal, FGTS, CNDT e Falência."
    )
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Validar no site oficial": st.column_config.LinkColumn(
                "Validar",
                display_text="Abrir site oficial",
            ),
        },
    )

    report = "\n".join(
        [
            "ROTEIRO DE CONFERÊNCIA E VALIDAÇÃO",
            "",
            *[
                (
                    f"{row['Fornecedor']} | {row['Documento']} | "
                    f"Validade: {row['Validade']} | Situação: {row['Situação']} | "
                    f"Consulta: {row['Validar no site oficial'] or row['Orientação']}"
                )
                for row in rows
            ],
        ]
    )
    st.download_button(
        "Baixar roteiro de validação",
        data=report.encode("utf-8"),
        file_name="ROTEIRO_DE_VALIDACAO_DOCUMENTAL.txt",
        mime="text/plain",
        use_container_width=True,
    )


def document_rows(analysis: dict) -> list[dict]:
    return [
        {
            "Selecionar": False,
            "ID": document["source"],
            "Grupo": document["document_group"],
            "Fornecedor": document["supplier"],
            "Arquivo original": document["name"],
            "Nome organizado": document["standardized_name"],
            "Identificado": "Sim" if document["identified"] else "Não",
            "Usado": "Sim" if document["selected_for_requirement"] else "Não",
            "Identificado por": document["identified_by"],
            "Validade": document["validity_date"] or "-",
            "Situação": document["validity_status"],
            "Validar no site oficial": document["validation_url"] or None,
            "Dados para consulta": document.get("validation_data", ""),
            "Categoria": document["category"],
            "Extensão": document["extension"],
            "Tamanho (KB)": round(document["size"] / 1024, 1),
        }
        for document in analysis["documents"]
        if document["extension"] == ".pdf"
    ]


def render_documents_tab(result: dict) -> None:
    analysis = result["analysis"]
    rows = document_rows(analysis)
    if not rows:
        st.info("Nenhum PDF localizado para seleção/impressão.")
        return

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
    selected_sources: list[str] = []
    for group_index, (group_name, group_tab) in enumerate(zip(group_names, group_tabs)):
        with group_tab:
            group_rows = [row for row in rows if row["Grupo"] == group_name]
            if not group_rows:
                st.caption("Nenhum documento localizado neste grupo.")
                continue
            edited_documents = st.data_editor(
                group_rows,
                use_container_width=True,
                hide_index=True,
                disabled=[column for column in group_rows[0] if column != "Selecionar"],
                column_config={
                    "Selecionar": st.column_config.CheckboxColumn(
                        "Imprimir",
                        help="Marque os documentos que deseja reunir para impressão.",
                        default=False,
                    ),
                    "ID": None,
                    "Grupo": None,
                    "Validar no site oficial": st.column_config.LinkColumn(
                        "Validar",
                        display_text="Abrir site oficial",
                    ),
                },
                key=f"foco_docs_print_selection_{group_index}",
            )
            selected_sources.extend(
                row["ID"] for row in edited_documents if row["Selecionar"]
            )

    st.caption(f"{len(selected_sources)} documento(s) selecionado(s) para impressão.")
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
                files = get_selected_pdf_documents(
                    result["source_bytes"],
                    analysis,
                    selected_sources,
                )
                st.session_state.foco_docs_print_result = {
                    "mode": "individual",
                    "files": files,
                    "documents": len(files),
                }
        except Exception as exc:
            st.error("Não consegui preparar os documentos selecionados.")
            with st.expander("Detalhes do erro"):
                st.code(f"{type(exc).__name__}: {exc}")

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
        st.success(f"{print_result['documents']} documento(s) preparado(s).")
        for index, document in enumerate(print_result["files"]):
            st.download_button(
                f"Baixar — {document['name']}",
                data=document["content"],
                file_name=document["name"],
                mime="application/pdf",
                use_container_width=True,
                key=f"download_individual_{index}_{document['name']}",
            )


def render_result() -> None:
    result = st.session_state.get("foco_docs_result")
    if not result:
        st.markdown(
            """
            <div class="foco-card">
                <div class="foco-section-title">Resultado final</div>
                <div class="foco-section-note">
                    Depois do processamento, você baixará um ZIP com os fornecedores
                    organizados em pastas e os documentos renomeados pelo item do edital.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info(
            "Depois do processamento, você baixará um ZIP com os fornecedores "
            "organizados em pastas e os documentos renomeados."
        )
        return

    analysis = result["analysis"]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Documentos", len(analysis["documents"]))
    metric_cols[1].metric("Básicos", analysis["totals"]["BÁSICOS"])
    metric_cols[2].metric("Técnicos", analysis["totals"]["TÉCNICOS"])
    metric_cols[3].metric("Não identificados", analysis["totals"]["NÃO CLASSIFICADOS"])
    st.caption(
        f"{len(analysis.get('suppliers', []))} fornecedor(es) localizado(s) no pacote."
    )
    if analysis.get("session_date"):
        st.info(
            "Validade dos documentos conferida com base na data da sessão: "
            f"{analysis['session_date']}."
        )

    tab_checklist, tab_validation, tab_documents = st.tabs(
        ["Checklist", "Conferência / validação", "Documentos e impressão"]
    )
    with tab_checklist:
        st.dataframe(analysis["checklist"], use_container_width=True, hide_index=True)
    with tab_validation:
        render_validation_tab(analysis)
    with tab_documents:
        render_documents_tab(result)

    st.download_button(
        "Baixar todos os fornecedores organizados",
        data=result["zip"],
        file_name="fornecedores_documentos_organizados.zip",
        mime="application/zip",
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="FOCO DOCS - Licita Suite-JM.adm",
        page_icon="📁",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()
    with st.sidebar:
        st.markdown("### FOCO DOCS")
        st.caption("Aplicativo exclusivo para separar documentos.")
        if portal_api_configured():
            st.success("API do Portal configurada com segurança.")
        else:
            st.warning("API do Portal ainda não configurada nos Secrets.")
            st.caption("Use o nome PORTAL_COMPRAS_API_KEY.")
        if st.button("Limpar resultado", use_container_width=True):
            st.session_state.pop("foco_docs_result", None)
            reset_print_selection()
            st.rerun()

    render_header()
    render_inputs()
    render_result()


if __name__ == "__main__":
    main()
