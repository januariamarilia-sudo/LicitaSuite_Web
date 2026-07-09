from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import PurePosixPath
import csv
import re
import unicodedata
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile


MAX_FILES = 2_000
MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024

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


def _safe_basename(name: str) -> str:
    basename = PurePosixPath(name.replace("\\", "/")).name
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", basename).strip(" .")
    return cleaned or "documento_sem_nome"


def analyze_document_zip(
    content: bytes,
    profile: str,
    technical_qualification: str = "",
) -> dict:
    if profile not in PROFILE_CHECKLISTS:
        raise ValueError(f"Perfil documental inválido: {profile}")

    try:
        archive = ZipFile(BytesIO(content))
    except BadZipFile as exc:
        raise ValueError("O arquivo enviado não é um ZIP válido.") from exc

    with archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        if len(entries) > MAX_FILES:
            raise ValueError(f"O ZIP excede o limite de {MAX_FILES} arquivos.")

        total_size = sum(entry.file_size for entry in entries)
        if total_size > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("O conteúdo descompactado excede o limite de 300 MB.")

        documents = []
        for entry in entries:
            filename = _safe_basename(entry.filename)
            suffix = PurePosixPath(filename).suffix.casefold()
            documents.append(
                {
                    "source": entry.filename,
                    "name": filename,
                    "category": classify_document(filename),
                    "extension": suffix or "sem extensão",
                    "size": entry.file_size,
                    "ocr_candidate": suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"},
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
    return {
        "profile": profile,
        "technical_qualification": technical_qualification.strip(),
        "documents": documents,
        "checklist": checklist,
        "totals": totals,
        "ocr_candidates": sum(document["ocr_candidate"] for document in documents),
    }


def build_organized_zip(content: bytes, analysis: dict) -> bytes:
    source_buffer = BytesIO(content)
    output_buffer = BytesIO()
    document_map = {
        document["source"]: document for document in analysis["documents"]
    }

    with ZipFile(source_buffer) as source, ZipFile(
        output_buffer, "w", ZIP_DEFLATED
    ) as target:
        for index, entry in enumerate(source.infolist(), start=1):
            if entry.is_dir() or entry.filename not in document_map:
                continue
            document = document_map[entry.filename]
            folder = {
                "BÁSICOS": "01_DOCUMENTOS_BASICOS",
                "TÉCNICOS": "02_DOCUMENTOS_TECNICOS",
                "NÃO CLASSIFICADOS": "03_NAO_CLASSIFICADOS",
            }[document["category"]]
            target.writestr(
                f"{folder}/{index:04d}_{document['name']}",
                source.read(entry),
            )

        report = StringIO()
        writer = csv.writer(report, delimiter=";")
        writer.writerow(["arquivo", "categoria", "extensao", "tamanho_bytes", "ocr"])
        for document in analysis["documents"]:
            writer.writerow(
                [
                    document["name"],
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

    return output_buffer.getvalue()
