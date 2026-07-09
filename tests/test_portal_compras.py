from portal.portal_compras import build_process_search_url


def test_build_process_search_url_uses_process_and_icismep():
    url = build_process_search_url("39/2026", "ICISMEP")

    assert "processo=39%2F2026" in url
    assert "orgao=ICISMEP" in url
