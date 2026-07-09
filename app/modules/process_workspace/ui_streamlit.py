import streamlit as st
from .service import ProcessWorkspaceService


def render_process_workspace(service: ProcessWorkspaceService):
    st.title("Central de Processos")

    with st.expander("Criar novo processo", expanded=True):
        process_number = st.text_input("Processo", placeholder="Ex.: 53/2026")
        modality = st.text_input("Modalidade", placeholder="Ex.: Pregão Eletrônico")
        object_description = st.text_area("Objeto", placeholder="Descrição resumida do objeto")

        if st.button("Criar workspace"):
            if process_number and modality and object_description:
                service.create_process(process_number, modality, object_description)
                st.success("Workspace criado com sucesso.")
            else:
                st.warning("Preencha processo, modalidade e objeto.")

    st.subheader("Processos cadastrados")

    term = st.text_input("Pesquisar", placeholder="Processo, fornecedor, modalidade, objeto...")
    processes = service.search(term) if term else service.list_processes()

    for process in processes:
        with st.container(border=True):
            dashboard = process.to_dashboard()
            st.markdown(f"### Processo {dashboard['processo']}")
            st.write(dashboard["objeto"])

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Status", dashboard["status"])
            col2.metric("Fornecedores", dashboard["fornecedores"])
            col3.metric("Itens", dashboard["itens"])
            col4.metric("Atas", dashboard["atas"])

            st.markdown("#### Linha do tempo")
            for event in process.timeline[-6:]:
                st.write(f"✓ {event.title} — {event.created_at.strftime('%d/%m/%Y %H:%M')}")
