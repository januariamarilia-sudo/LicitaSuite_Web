from __future__ import annotations

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


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --navy: #10213f;
            --blue: #175cd3;
            --blue-soft: #eef4ff;
            --green: #067647;
            --amber: #b54708;
            --canvas: #f6f8fc;
            --border: #d8dfeb;
            --muted: #667085;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(23,92,211,.10), transparent 30rem),
                linear-gradient(180deg, #fbfcff 0%, var(--canvas) 100%);
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #10213f 0%, #132c55 100%);
        }
        section[data-testid="stSidebar"] * {
            color: #ffffff !important;
        }
        .foco-hero {
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.35rem 1.45rem;
            background: rgba(255,255,255,.92);
            box-shadow: 0 18px 45px rgba(16,33,63,.08);
            margin-bottom: 1rem;
        }
        .foco-eyebrow {
            color: var(--blue);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin-bottom: .25rem;
        }
        .foco-title {
            color: var(--navy);
            font-size: 2rem;
            line-height: 1.05;
            font-weight: 850;
            margin: 0;
        }
        .foco-subtitle {
            color: var(--muted);
            font-size: .98rem;
            margin-top: .45rem;
            max-width: 58rem;
        }
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 12px;
            font-weight: 750;
        }
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,.88);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: .85rem 1rem;
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
                documentos de fornecedores organizados por pasta.
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
    st.markdown("### 1. Envie o pacote documental")
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
        if st.button("Limpar resultado", use_container_width=True):
            st.session_state.pop("foco_docs_result", None)
            reset_print_selection()
            st.rerun()

    render_header()
    render_inputs()
    render_result()


if __name__ == "__main__":
    main()
