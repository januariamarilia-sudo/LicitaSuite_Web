from portal.portal_compras import (
    build_process_search_url,
    extract_supplier_names_from_process_page,
)


def test_build_process_search_url_uses_process_and_icismep():
    url = build_process_search_url("39/2026", "ICISMEP")

    assert "processo=39%2F2026" in url
    assert "orgao=ICISMEP" in url


def test_extract_supplier_names_from_process_page():
    html = """
    <main>
      <h2>Documentos</h2>
      <button>Processo</button><button>Fornecedores</button>
      <section>
        <div>Bh Farma Comércio Ltda</div><button>BAIXAR TUDO</button>
        <div>Med Center Comercial Ltda</div><button>BAIXAR TUDO</button>
      </section>
      <h2>Itens</h2>
    </main>
    """

    suppliers = extract_supplier_names_from_process_page(html)

    assert suppliers == [
        "Bh Farma Comércio Ltda",
        "Med Center Comercial Ltda",
    ]
