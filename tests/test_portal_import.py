def test_portal_import():
    from portal import app

    assert "Gerar atas" in app.PAGES
    assert callable(app.legacy_app_module)
