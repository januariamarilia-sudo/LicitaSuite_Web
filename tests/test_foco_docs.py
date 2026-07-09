from io import BytesIO
from zipfile import ZipFile

from portal.foco_docs import analyze_document_zip, build_organized_zip


def _sample_zip() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("fornecedor/CNPJ.pdf", b"cnpj")
        archive.writestr("fornecedor/Atestado Capacidade Tecnica.pdf", b"atestado")
        archive.writestr("fornecedor/foto_documento.png", b"image")
    return buffer.getvalue()


def test_foco_docs_classifies_and_repackages_documents():
    source = _sample_zip()
    qualification = "Licença sanitária e AFE da ANVISA."
    analysis = analyze_document_zip(source, "Genérico", qualification)

    assert analysis["technical_qualification"] == qualification
    assert analysis["totals"] == {
        "BÁSICOS": 1,
        "TÉCNICOS": 1,
        "NÃO CLASSIFICADOS": 1,
    }
    assert analysis["ocr_candidates"] == 1

    organized = build_organized_zip(source, analysis)
    with ZipFile(BytesIO(organized)) as archive:
        names = archive.namelist()
        assert any(name.startswith("01_DOCUMENTOS_BASICOS/") for name in names)
        assert any(name.startswith("02_DOCUMENTOS_TECNICOS/") for name in names)
        assert "RELATORIO_INTELIGENCIA_DOCUMENTAL.csv" in names
        assert "CHECKLIST_DOCUMENTAL.txt" in names
        checklist = archive.read("CHECKLIST_DOCUMENTAL.txt").decode("utf-8")
        assert "QUALIFICAÇÃO TÉCNICA EXIGIDA" in checklist
        assert qualification in checklist
