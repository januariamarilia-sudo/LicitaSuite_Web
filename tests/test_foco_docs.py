from io import BytesIO
import tarfile
from zipfile import ZipFile

from portal.foco_docs import analyze_document_zip, build_organized_zip


def _sample_zip() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("fornecedor/CNPJ.pdf", b"cnpj")
        archive.writestr("fornecedor/Atestado Capacidade Tecnica.pdf", b"atestado")
        archive.writestr("fornecedor/foto_documento.png", b"image")
    return buffer.getvalue()


def _nested_zip() -> bytes:
    supplier_buffer = BytesIO()
    with ZipFile(supplier_buffer, "w") as supplier_archive:
        supplier_archive.writestr("Contrato Social.pdf", b"contrato")

    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("EMPRESA EXEMPLO.zip", supplier_buffer.getvalue())
    return buffer.getvalue()


def _zip_with_tar() -> bytes:
    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
        content = b"cnd"
        info = tarfile.TarInfo("4 CND ESTADUAL.pdf")
        info.size = len(content)
        archive.addfile(info, BytesIO(content))

    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("HABILITAÇÃO.tar", tar_buffer.getvalue())
    return buffer.getvalue()


def test_foco_docs_classifies_and_repackages_documents():
    source = _sample_zip()
    qualification = "Licença sanitária e AFE da ANVISA."
    analysis = analyze_document_zip(source, "Genérico", qualification)

    assert analysis["technical_qualification"] == qualification
    assert analysis["suppliers"] == ["fornecedor"]
    assert analysis["totals"] == {
        "BÁSICOS": 1,
        "TÉCNICOS": 1,
        "NÃO CLASSIFICADOS": 1,
    }
    assert analysis["ocr_candidates"] == 1

    organized = build_organized_zip(
        source,
        analysis,
        ("relatorio_itens_vencidos.csv", b"fornecedor;item"),
    )
    with ZipFile(BytesIO(organized)) as archive:
        names = archive.namelist()
        assert (
            "fornecedor/01 - Documentos Exigidos/"
            "7.2.1 - Comprovante de CNPJ.pdf"
            in names
        )
        assert (
            "fornecedor/02 - Documentos Não Utilizados/"
            "Atestado Capacidade Tecnica.pdf"
            in names
        )
        assert (
            "fornecedor/03 - Documentos Não Identificados/foto_documento.png"
            in names
        )
        assert "fornecedor/RELATÓRIO DE CONFERÊNCIA.txt" in names
        assert "00 - Referência/relatorio_itens_vencidos.csv" in names
        assert "RELATORIO_INTELIGENCIA_DOCUMENTAL.csv" in names
        assert "CHECKLIST_DOCUMENTAL.txt" in names
        checklist = archive.read("CHECKLIST_DOCUMENTAL.txt").decode("utf-8")
        assert "QUALIFICAÇÃO TÉCNICA EXIGIDA" in checklist
        assert qualification in checklist


def test_foco_docs_extracts_nested_supplier_zip():
    source = _nested_zip()
    analysis = analyze_document_zip(source, "Genérico")

    assert analysis["suppliers"] == ["EMPRESA EXEMPLO"]
    assert analysis["documents"][0]["standardized_name"].startswith("7.1.1 -")

    organized = build_organized_zip(source, analysis)
    with ZipFile(BytesIO(organized)) as archive:
        assert (
            "EMPRESA EXEMPLO/01 - Documentos Exigidos/"
            "7.1.1 - Contrato Social.pdf"
            in archive.namelist()
        )


def test_foco_docs_extracts_tar_inside_zip():
    source = _zip_with_tar()
    analysis = analyze_document_zip(
        source,
        "Padrão geral",
        default_supplier="FORNECEDOR TESTE",
    )

    assert len(analysis["documents"]) == 1
    assert analysis["documents"][0]["document_code"] == "7.2.3"
    assert analysis["documents"][0]["supplier"] == "FORNECEDOR TESTE"


def test_foco_docs_flags_expired_validity_from_filename():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "FORNECEDOR/CNPJ - VAL. 01-01-2020.pdf",
            b"documento",
        )

    analysis = analyze_document_zip(buffer.getvalue(), "Padrão geral")
    document = analysis["documents"][0]

    assert document["validity_date"] == "01/01/2020"
    assert document["validity_status"] == "Vencido"
