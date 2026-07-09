from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import PurePosixPath
import csv
import re
import unicodedata
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import pdfplumber
from docx import Document


MAX_FILES = 2_000
MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024
MAX_NESTED_ZIP_DEPTH = 4
MAX_TEXT_EXTRACTION_PAGES = 5
CONDITIONAL_DOCUMENT_CODES = {"7.1.2", "7.1.3"}

DOCUMENT_RULES = (
    ("7.0.1", "SICAF", "BÁSICOS", ("sicaf",)),
    ("7.0.2", "Proposta Comercial", "BÁSICOS", ("proposta",)),
    ("7.0.3", "Requerimento", "BÁSICOS", ("requerimento",)),
    ("7.0.4", "Catálogo dos Itens Vencedores", "TÉCNICOS", ("catalogo", "catálogo")),
    (
        "7.1.1",
        "Contrato Social",
        "BÁSICOS",
        ("contrato social", "estatuto", "ato constitutivo"),
    ),
    (
        "7.1.2",
        "Procuração e Documento do Representante",
        "BÁSICOS",
        ("procuracao", "procuração", "representante", "rg cpf"),
    ),
    (
        "7.1.3",
        "Autorização de Empresa Estrangeira",
        "BÁSICOS",
        ("empresa estrangeira", "autorizacao funcionamento estrangeira"),
    ),
    ("7.2.1", "Comprovante de CNPJ", "BÁSICOS", ("cnpj",)),
    (
        "7.2.2",
        "Certidão Federal",
        "BÁSICOS",
        ("certidao federal", "certidão federal", "receita federal"),
    ),
    (
        "7.2.3",
        "Certidão Estadual",
        "BÁSICOS",
        ("certidao estadual", "certidão estadual", "fazenda estadual"),
    ),
    (
        "7.2.4",
        "Certidão Municipal",
        "BÁSICOS",
        ("certidao municipal", "certidão municipal", "fazenda municipal"),
    ),
    ("7.2.5", "Certificado de Regularidade do FGTS", "BÁSICOS", ("fgts", "crf")),
    (
        "7.2.6",
        "Certidão Negativa de Débitos Trabalhistas",
        "BÁSICOS",
        ("cndt", "debitos trabalhistas", "débitos trabalhistas"),
    ),
    (
        "7.3.1",
        "Certidão de Falência",
        "BÁSICOS",
        ("falencia", "falência", "recuperacao judicial", "recuperação judicial"),
    ),
    (
        "10.9.1",
        "Licença Sanitária",
        "TÉCNICOS",
        ("licenca sanitaria", "licença sanitária", "alvara sanitario", "alvará sanitário"),
    ),
    (
        "10.9.2",
        "AFE ANVISA",
        "TÉCNICOS",
        ("afe anvisa", "autorizacao de funcionamento", "autorização de funcionamento"),
    ),
    (
        "10.9.3",
        "Registro ANVISA",
        "TÉCNICOS",
        ("registro anvisa", "registro do produto", "publicacao dou", "publicação dou"),
    ),
    (
        "10.9.5",
        "Declaração de Isenção",
        "TÉCNICOS",
        ("declaracao de isencao", "declaração de isenção", "isento anvisa"),
    ),
    (
        "10.9",
        "Atestado de Capacidade Técnica",
        "TÉCNICOS",
        ("atestado", "capacidade tecnica", "capacidade técnica"),
    ),
)

BASIC_KEYWORDS = (
    "cnpj",
    "contrato social",
    "estatuto",
    "certidao",
    "certidão",
    "fgts",
    "cndt",
    "falencia",
    "falência",
    "inscricao estadual",
    "inscrição estadual",
    "alvara",
    "alvará",
    "documento representante",
    "identidade",
)

TECHNICAL_KEYWORDS = (
    "atestado",
    "capacidade tecnica",
    "capacidade técnica",
    "responsavel tecnico",
    "responsável técnico",
    "conselho",
    "vigilancia sanitaria",
    "vigilância sanitária",
    "anvisa",
    "licenca",
    "licença",
    "autorizacao",
    "autorização",
    "qualificacao tecnica",
    "qualificação técnica",
    "certificado",
)

PROFILE_CHECKLISTS = {
    "Genérico": (
        ("CNPJ", ("cnpj",)),
        ("Ato constitutivo", ("contrato social", "estatuto")),
        ("Regularidade fiscal", ("certidao", "certidão", "fgts")),
        ("Regularidade trabalhista", ("cndt", "trabalhista")),
        ("Qualificação técnica", ("atestado", "capacidade tecnica", "capacidade técnica")),
    ),
    "Laboratório": (
        ("CNPJ", ("cnpj",)),
        ("Licença sanitária", ("licenca sanitaria", "licença sanitária")),
        ("Responsável técnico", ("responsavel tecnico", "responsável técnico")),
        ("Conselho profissional", ("conselho", "crf", "crbm", "crm")),
        ("Atestado de capacidade", ("atestado", "capacidade tecnica", "capacidade técnica")),
    ),
    "Ambulância": (
        ("CNPJ", ("cnpj",)),
        ("Licença sanitária", ("licenca sanitaria", "licença sanitária")),
        ("Documentação dos veículos", ("veiculo", "veículo", "crlv")),
        ("Responsável técnico", ("responsavel tecnico", "responsável técnico")),
        ("Atestado de capacidade", ("atestado", "capacidade tecnica", "capacidade técnica")),
    ),
    "Medicamentos": (
        ("CNPJ", ("cnpj",)),
        ("AFE/ANVISA", ("afe", "anvisa")),
        ("Licença sanitária", ("licenca sanitaria", "licença sanitária")),
        ("Responsável técnico", ("responsavel tecnico", "responsável técnico", "crf")),
        ("Atestado de capacidade", ("atestado", "capacidade tecnica", "capacidade técnica")),
    ),
}


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def classify_document(filename: str) -> str:
    normalized = normalize_text(filename)
    if any(normalize_text(keyword) in normalized for keyword in BASIC_KEYWORDS):
        return "BÁSICOS"
    if any(normalize_text(keyword) in normalized for keyword in TECHNICAL_KEYWORDS):
        return "TÉCNICOS"
    return "NÃO CLASSIFICADOS"


def identify_document(filename: str, extracted_text: str = "") -> dict | None:
    normalized = normalize_text(f"{filename} {extracted_text}")
    for code, label, category, keywords in DOCUMENT_RULES:
        if any(normalize_text(keyword) in normalized for keyword in keywords):
            return {"code": code, "label": label, "category": category}
    return None


def _extract_searchable_text(filename: str, content: bytes) -> str:
    suffix = PurePosixPath(filename).suffix.casefold()
    try:
        if suffix == ".pdf":
            with pdfplumber.open(BytesIO(content)) as pdf:
                return " ".join(
                    page.extract_text() or ""
                    for page in pdf.pages[:MAX_TEXT_EXTRACTION_PAGES]
                )[:30_000]
        if suffix == ".docx":
            document = Document(BytesIO(content))
            return " ".join(paragraph.text for paragraph in document.paragraphs)[
                :30_000
            ]
    except Exception:
        return ""
    return ""


def _extract_all_zip_documents(
    content: bytes,
    *,
    prefix: str = "",
    depth: int = 0,
    limits: dict | None = None,
) -> list[dict]:
    if limits is None:
        limits = {"files": 0, "bytes": 0}
    if depth > MAX_NESTED_ZIP_DEPTH:
        raise ValueError(
            f"O pacote contém mais de {MAX_NESTED_ZIP_DEPTH} níveis de ZIP."
        )

    try:
        archive = ZipFile(BytesIO(content))
    except BadZipFile as exc:
        raise ValueError("O arquivo enviado não é um ZIP válido.") from exc

    extracted = []
    with archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            source = (
                f"{prefix}/{entry.filename}".strip("/")
                if prefix
                else entry.filename
            )
            payload = archive.read(entry)
            if PurePosixPath(entry.filename).suffix.casefold() == ".zip":
                try:
                    extracted.extend(
                        _extract_all_zip_documents(
                            payload,
                            prefix=source,
                            depth=depth + 1,
                            limits=limits,
                        )
                    )
                    continue
                except BadZipFile:
                    pass
                except ValueError as exc:
                    if "não é um ZIP válido" not in str(exc):
                        raise

            limits["files"] += 1
            limits["bytes"] += len(payload)
            if limits["files"] > MAX_FILES:
                raise ValueError(f"O ZIP excede o limite de {MAX_FILES} arquivos.")
            if limits["bytes"] > MAX_UNCOMPRESSED_BYTES:
                raise ValueError(
                    "O conteúdo descompactado excede o limite de 300 MB."
                )
            extracted.append({"source": source, "content": payload})
    return extracted


def _safe_basename(name: str) -> str:
    basename = PurePosixPath(name.replace("\\", "/")).name
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", basename).strip(" .")
    return cleaned or "documento_sem_nome"


def _supplier_from_source(source: str) -> str:
    parts = [
        part
        for part in source.replace("\\", "/").split("/")
        if part and part not in {".", ".."}
    ]
    if len(parts) < 2:
        return "FORNECEDOR_NAO_IDENTIFICADO"
    supplier_part = (
        PurePosixPath(parts[0]).stem
        if PurePosixPath(parts[0]).suffix.casefold() == ".zip"
        else parts[0]
    )
    cleaned = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        "_",
        supplier_part,
    ).strip(" .")
    return cleaned or "FORNECEDOR_NAO_IDENTIFICADO"


def analyze_document_zip(
    content: bytes,
    profile: str,
    technical_qualification: str = "",
) -> dict:
    if profile not in PROFILE_CHECKLISTS:
        raise ValueError(f"Perfil documental inválido: {profile}")

    entries = _extract_all_zip_documents(content)
    documents = []
    for entry in entries:
        filename = _safe_basename(entry["source"])
        suffix = PurePosixPath(filename).suffix.casefold()
        searchable_text = _extract_searchable_text(filename, entry["content"])
        identification = identify_document(filename, searchable_text)
        standardized_name = (
            f"{identification['code']} {identification['label']}{suffix}"
            if identification
            else filename
        )
        documents.append(
            {
                "source": entry["source"],
                "supplier": _supplier_from_source(entry["source"]),
                "name": filename,
                "standardized_name": standardized_name,
                "identified": identification is not None,
                "document_code": identification["code"] if identification else "",
                "document_label": identification["label"] if identification else "",
                "category": (
                    identification["category"]
                    if identification
                    else "NÃO CLASSIFICADOS"
                ),
                "extension": suffix or "sem extensão",
                "size": len(entry["content"]),
                "ocr_candidate": suffix
                in {".png", ".jpg", ".jpeg", ".tif", ".tiff"},
            }
        )

    all_names = " ".join(document["name"] for document in documents)
    normalized_names = normalize_text(all_names)
    checklist = []
    for label, keywords in PROFILE_CHECKLISTS[profile]:
        found = any(normalize_text(keyword) in normalized_names for keyword in keywords)
        checklist.append({"document": label, "status": "Localizado" if found else "Pendente"})

    totals = {
        category: sum(document["category"] == category for document in documents)
        for category in ("BÁSICOS", "TÉCNICOS", "NÃO CLASSIFICADOS")
    }
    suppliers = sorted({document["supplier"] for document in documents})
    return {
        "profile": profile,
        "technical_qualification": technical_qualification.strip(),
        "documents": documents,
        "suppliers": suppliers,
        "checklist": checklist,
        "totals": totals,
        "ocr_candidates": sum(document["ocr_candidate"] for document in documents),
    }


def build_organized_zip(
    content: bytes,
    analysis: dict,
    reference_file: tuple[str, bytes] | None = None,
) -> bytes:
    output_buffer = BytesIO()
    document_map = {
        document["source"]: document for document in analysis["documents"]
    }
    extracted_entries = _extract_all_zip_documents(content)

    with ZipFile(output_buffer, "w", ZIP_DEFLATED) as target:
        output_names: dict[str, int] = {}
        for entry in extracted_entries:
            if entry["source"] not in document_map:
                continue
            document = document_map[entry["source"]]
            if document["identified"]:
                folder = (
                    f"{document['supplier']}/01 - Documentos Exigidos"
                )
                desired_name = document["standardized_name"]
            else:
                folder = (
                    f"{document['supplier']}/02 - Documentos Não Identificados"
                )
                desired_name = document["name"]

            collision_key = f"{folder}/{desired_name}".casefold()
            output_names[collision_key] = output_names.get(collision_key, 0) + 1
            occurrence = output_names[collision_key]
            if occurrence > 1:
                path = PurePosixPath(desired_name)
                desired_name = f"{path.stem} ({occurrence}){path.suffix}"

            target.writestr(
                f"{folder}/{desired_name}",
                entry["content"],
            )

        report = StringIO()
        writer = csv.writer(report, delimiter=";")
        writer.writerow(
            [
                "arquivo_original",
                "arquivo_renomeado",
                "fornecedor",
                "identificado",
                "codigo",
                "categoria",
                "extensao",
                "tamanho_bytes",
                "ocr",
            ]
        )
        for document in analysis["documents"]:
            writer.writerow(
                [
                    document["name"],
                    document["standardized_name"],
                    document["supplier"],
                    "sim" if document["identified"] else "não",
                    document["document_code"],
                    document["category"],
                    document["extension"],
                    document["size"],
                    "sim" if document["ocr_candidate"] else "não",
                ]
            )
        target.writestr(
            "RELATORIO_INTELIGENCIA_DOCUMENTAL.csv",
            report.getvalue().encode("utf-8-sig"),
        )

        checklist_lines = [
            f"Perfil documental: {analysis['profile']}",
            "",
            "QUALIFICAÇÃO TÉCNICA EXIGIDA:",
            analysis.get("technical_qualification")
            or "Não informada para este processo.",
            "",
            *[
                f"[{'OK' if item['status'] == 'Localizado' else '  '}] "
                f"{item['document']} — {item['status']}"
                for item in analysis["checklist"]
            ],
        ]
        target.writestr(
            "CHECKLIST_DOCUMENTAL.txt",
            "\n".join(checklist_lines).encode("utf-8"),
        )

        if reference_file:
            reference_name, reference_content = reference_file
            target.writestr(
                f"00 - Referência/{_safe_basename(reference_name)}",
                reference_content,
            )

        for supplier in analysis.get("suppliers", []):
            supplier_documents = [
                document
                for document in analysis["documents"]
                if document["supplier"] == supplier
            ]
            located_codes = {
                document["document_code"]
                for document in supplier_documents
                if document["identified"]
            }
            supplier_lines = [
                f"Fornecedor: {supplier}",
                f"Perfil documental: {analysis['profile']}",
                "",
                "QUALIFICAÇÃO TÉCNICA EXIGIDA (OPCIONAL):",
                analysis.get("technical_qualification") or "Não informada.",
                "",
                "DOCUMENTOS LOCALIZADOS:",
                *[
                    f"[OK] {document['document_code']} - {document['document_label']}"
                    for document in supplier_documents
                    if document["identified"]
                ],
                "",
                "DOCUMENTOS BÁSICOS NÃO LOCALIZADOS:",
                *[
                    f"[  ] {code} - {label}"
                    for code, label, category, _ in DOCUMENT_RULES
                    if (
                        category == "BÁSICOS"
                        and code not in located_codes
                        and code not in CONDITIONAL_DOCUMENT_CODES
                    )
                ],
                "",
                "DOCUMENTOS CONDICIONAIS — CONFERIR APLICABILIDADE:",
                *[
                    f"[{'OK' if code in located_codes else '  '}] {code} - {label}"
                    for code, label, _, _ in DOCUMENT_RULES
                    if code in CONDITIONAL_DOCUMENT_CODES
                ],
            ]
            target.writestr(
                f"{supplier}/RELATÓRIO DE CONFERÊNCIA.txt",
                "\n".join(supplier_lines).encode("utf-8"),
            )

    return output_buffer.getvalue()
