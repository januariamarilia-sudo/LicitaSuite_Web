from io import BytesIO
import tarfile
from zipfile import ZipFile

from pypdf import PdfReader, PdfWriter

from portal.foco_docs import (
    analyze_document_zip,
    build_organized_zip,
    build_print_pdf,
    document_validation,
)


def _sample_zip() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("fornecedor/CNPJ.pdf", b"cnpj")
        archive.writestr("fornecedor/Certidao Simplificada.pdf", b"certidao simplificada")
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
    groups = {
        document["name"]: document["document_group"]
        for document in analysis["documents"]
    }
    assert groups["CNPJ.pdf"] == "Regularidade fiscal"
    assert (
        groups["Atestado Capacidade Tecnica.pdf"]
        == "Qualificação técnica"
    )
    assert groups["foto_documento.png"] == "Outros documentos"
    cnpj_document = next(
        document
        for document in analysis["documents"]
        if document["name"] == "CNPJ.pdf"
    )
    assert "receita.fazenda.gov.br" in cnpj_document["validation_url"]
    assert analysis["totals"] == {
        "BÁSICOS": 2,
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
            "fornecedor/03 - Documentos de Habilitação/"
            "10.7.1 - Comprovante de CNPJ.pdf"
            in names
        )
        assert (
            "fornecedor/03 - Documentos de Habilitação/"
            "10.6.4 - Certidão Simplificada ME EPP.pdf"
            in names
        )
        assert (
            "fornecedor/02 - Consulta TCU e CEIS-CNEP/"
            "02 - Roteiro de consulta.txt"
            in names
        )
        assert (
            "fornecedor/01 - Documento do Processo/"
            "01 - relatorio_itens_vencidos.csv"
            in names
        )
        assert (
            "fornecedor/06 - Documentos Fora da Lista/"
            "Atestado Capacidade Tecnica.pdf"
            in names
        )
        assert (
            "fornecedor/07 - Documentos Não Identificados/foto_documento.png"
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
    assert analysis["documents"][0]["standardized_name"].startswith("10.6.1 -")

    organized = build_organized_zip(source, analysis)
    with ZipFile(BytesIO(organized)) as archive:
        assert (
            "EMPRESA EXEMPLO/03 - Documentos de Habilitação/"
            "10.6.1 - Ato Constitutivo e Contrato Social.pdf"
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
    assert analysis["documents"][0]["document_code"] == "10.7.3"
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


def test_foco_docs_builds_one_pdf_from_selected_documents():
    pdf_buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.write(pdf_buffer)

    package = BytesIO()
    with ZipFile(package, "w") as archive:
        archive.writestr("FORNECEDOR/CNPJ.pdf", pdf_buffer.getvalue())
        archive.writestr("FORNECEDOR/Outro.pdf", pdf_buffer.getvalue())

    source = package.getvalue()
    analysis = analyze_document_zip(source, "Padrão geral")
    selected = [document["source"] for document in analysis["documents"]]
    print_pdf, document_count, page_count = build_print_pdf(
        source,
        analysis,
        selected,
    )

    assert document_count == 2
    assert page_count == 2
    assert len(PdfReader(BytesIO(print_pdf)).pages) == 2


def test_foco_docs_uses_official_regional_validation_url_from_document():
    url, note = document_validation(
        "10.7.3",
        "Valide esta certidão em https://www.fazenda.mg.gov.br/validar",
    )

    assert url == "https://www.fazenda.mg.gov.br/validar"
    assert "localizado no documento" in note
