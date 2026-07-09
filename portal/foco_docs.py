from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import PurePosixPath
import csv
from datetime import date, datetime
import re
import tarfile
import unicodedata
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import pdfplumber
from docx import Document
from pypdf import PdfReader, PdfWriter

from licitasuite.parsers.vencedores_pdf_robusto import parse_vencedores_pdf_text


MAX_FILES = 2_000
MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024
MAX_NESTED_ZIP_DEPTH = 4
CONDITIONAL_DOCUMENT_CODES = {"7.1.2", "7.1.3"}
STANDARD_REQUIRED_CODES = {
    "7.0.1",
    "7.0.2",
    "7.0.3",
    "7.0.4",
    "7.1.1",
    "7.2.1",
    "7.2.2",
    "7.2.3",
    "7.2.4",
    "7.2.5",
    "7.2.6",
    "7.3.1",
}
MULTIPLE_DOCUMENT_CODES = {"7.1.1", "10.9.3"}

DOCUMENT_RULES = (
    ("7.0.1", "SICAF", "BÁSICOS", ("sicaf",)),
    (
        "7.0.2",
        "Proposta Comercial",
        "BÁSICOS",
        ("proposta", "realinhada"),
    ),
    ("7.0.3", "Requerimento", "BÁSICOS", ("requerimento",)),
    (
        "7.0.4",
        "Catálogo Itens Vencedores",
        "TÉCNICOS",
        (
            "catalogo",
            "catálogo",
            "folder",
            "prospecto",
            "ficha tecnica",
            "ficha técnica",
            "_cat",
        ),
    ),
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
        (
            "certidao federal",
            "certidão federal",
            "receita federal",
            "cnd federal",
            "cnd unificada",
        ),
    ),
    (
        "7.2.3",
        "Certidão Estadual",
        "BÁSICOS",
        (
            "certidao estadual",
            "certidão estadual",
            "fazenda estadual",
            "cnd estadual",
        ),
    ),
    (
        "7.2.4",
        "Certidão Municipal",
        "BÁSICOS",
        (
            "certidao municipal",
            "certidão municipal",
            "fazenda municipal",
            "cnd municipal",
        ),
    ),
    (
        "10.9",
        "Certificado de Regularidade Técnica",
        "TÉCNICOS",
        (
            "certificado de regularidade tecnica",
            "certificado de regularidade técnica",
            "certidao de regularidade tecnica",
            "certidão de regularidade técnica",
            "certificado regularidade tecnica",
            "certificado regularidade técnica",
            "crt empresa",
            "crt audio",
            "crf carteirinha",
            "crf + carteirinha",
        ),
    ),
    ("7.2.5", "FGTS", "BÁSICOS", ("fgts", "crf caixa", "regularidade do fgts")),
    (
        "7.2.6",
        "Certidão Negativa de Débitos Trabalhistas",
        "BÁSICOS",
        (
            "cndt",
            "debitos trabalhistas",
            "débitos trabalhistas",
            "cnd trabalhista",
        ),
    ),
    (
        "7.3.1",
        "Certidão de Falência",
        "BÁSICOS",
        ("falencia", "falência", "recuperacao judicial", "recuperação judicial"),
    ),
    (
        "10.9.1",
        "Alvará Sanitário",
        "TÉCNICOS",
        ("alvara sanitario", "alvará sanitário"),
    ),
    (
        "10.9.1",
        "Licença Sanitária",
        "TÉCNICOS",
        ("licenca sanitaria", "licença sanitária", "licenca de funcionamento"),
    ),
    (
        "10.9.2",
        "AFE ANVISA",
        "TÉCNICOS",
        (
            "afe anvisa",
            "autorizacao de funcionamento",
            "autorização de funcionamento",
            "aut. c-e-c",
            "aut c-e-c",
        ),
    ),
    (
        "10.9.3",
        "Registro ANVISA",
        "TÉCNICOS",
        (
            "registro anvisa",
            "registro do produto",
            "publicacao dou",
            "publicação dou",
            "_rms",
        ),
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

CONTENT_RULES = (
    (
        "7.0.1",
        "SICAF",
        "BÁSICOS",
        (("sistema de cadastramento unificado de fornecedores",),),
    ),
    (
        "7.0.2",
        "Proposta Comercial",
        "BÁSICOS",
        (("proposta comercial",),),
    ),
    (
        "7.0.3",
        "Requerimento",
        "BÁSICOS",
        (("requerimento de participacao",),),
    ),
    (
        "7.0.4",
        "Catálogo Itens Vencedores",
        "TÉCNICOS",
        (("catalogo de produtos",), ("prospecto tecnico",)),
    ),
    (
        "7.1.1",
        "Contrato Social",
        "BÁSICOS",
        (("contrato social",), ("alteracao contratual",), ("ato constitutivo",)),
    ),
    (
        "7.1.2",
        "Procuração e Documento do Representante",
        "BÁSICOS",
        (("instrumento de procuracao",), ("outorgante", "outorgado")),
    ),
    (
        "7.1.3",
        "Autorização de Empresa Estrangeira",
        "BÁSICOS",
        (("decreto de autorizacao", "empresa estrangeira"),),
    ),
    (
        "7.2.1",
        "Comprovante de CNPJ",
        "BÁSICOS",
        (("comprovante de inscricao e de situacao cadastral",),),
    ),
    (
        "7.2.2",
        "Certidão Federal",
        "BÁSICOS",
        (
            ("debitos relativos a creditos tributarios federais",),
            ("divida ativa da uniao", "certidao"),
        ),
    ),
    (
        "7.2.3",
        "Certidão Estadual",
        "BÁSICOS",
        (
            ("certidao", "fazenda estadual"),
            ("certidao", "secretaria de estado da fazenda"),
        ),
    ),
    (
        "7.2.4",
        "Certidão Municipal",
        "BÁSICOS",
        (
            ("certidao", "debitos municipais"),
            ("certidao", "fazenda municipal"),
            ("certidao mobiliaria",),
        ),
    ),
    (
        "7.2.5",
        "FGTS",
        "BÁSICOS",
        (("certificado de regularidade do fgts",), ("regularidade do fgts", "caixa")),
    ),
    (
        "7.2.6",
        "Certidão Negativa de Débitos Trabalhistas",
        "BÁSICOS",
        (("certidao negativa de debitos trabalhistas",),),
    ),
    (
        "7.3.1",
        "Certidão de Falência",
        "BÁSICOS",
        (
            ("certidao", "falencia"),
            ("certidao", "recuperacao judicial"),
        ),
    ),
    (
        "10.9.1",
        "Alvará Sanitário",
        "TÉCNICOS",
        (("alvara sanitario",),),
    ),
    (
        "10.9.1",
        "Licença Sanitária",
        "TÉCNICOS",
        (("licenca sanitaria",),),
    ),
    (
        "10.9.2",
        "AFE ANVISA",
        "TÉCNICOS",
        (("autorizacao de funcionamento", "anvisa"),),
    ),
    (
        "10.9.3",
        "Registro ANVISA",
        "TÉCNICOS",
        (("registro do produto", "anvisa"), ("registro anvisa",)),
    ),
    (
        "10.9",
        "Certificado de Regularidade Técnica",
        "TÉCNICOS",
        (
            ("certificado de regularidade tecnica",),
            ("certificado", "conselho regional", "responsavel tecnico"),
        ),
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
    "Padrão geral": (
        ("SICAF", ("sicaf",)),
        ("Proposta Comercial", ("proposta",)),
        ("Requerimento", ("requerimento",)),
        ("Catálogo dos itens vencedores", ("catalogo", "catálogo", "folder")),
        ("Contrato Social", ("contrato social", "estatuto", "ato constitutivo")),
        ("CNPJ", ("cnpj",)),
        ("Certidão Federal", ("certidao federal", "certidão federal")),
        ("Certidão Estadual", ("certidao estadual", "certidão estadual")),
        ("Certidão Municipal", ("certidao municipal", "certidão municipal")),
        ("FGTS", ("fgts",)),
        ("CNDT", ("cndt",)),
        ("Certidão de Falência", ("falencia", "falência")),
    ),
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
    normalized = normalize_text(filename)
    for code, label, category, keywords in DOCUMENT_RULES:
        if any(normalize_text(keyword) in normalized for keyword in keywords):
            explicit_code = re.search(
                rf"(?<!\d){re.escape(code)}(?!\d)",
                filename,
            )
            confidence = 100 if explicit_code else 80
            if "consolidada" in normalized or "consolidadas" in normalized:
                confidence = min(confidence, 60)
            return {
                "code": code,
                "label": label,
                "category": category,
                "confidence": confidence,
                "identified_by": "nome do arquivo",
            }

    normalized_content = normalize_text(extracted_text)
    for code, label, category, signatures in CONTENT_RULES:
        if any(
            all(normalize_text(term) in normalized_content for term in signature)
            for signature in signatures
        ):
            return {
                "code": code,
                "label": label,
                "category": category,
                "confidence": 50,
                "identified_by": "conteúdo do documento",
            }
    return None


def _ocr_document(filename: str, content: bytes) -> str:
    try:
        import fitz
        import pytesseract
        from PIL import Image

        suffix = PurePosixPath(filename).suffix.casefold()
        if suffix == ".pdf":
            pdf = fitz.open(stream=content, filetype="pdf")
            texts = []
            for page in pdf:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
                image = Image.open(BytesIO(pixmap.tobytes("png")))
                texts.append(pytesseract.image_to_string(image, lang="por"))
            return "\n".join(texts)
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            return pytesseract.image_to_string(
                Image.open(BytesIO(content)),
                lang="por",
            )
    except Exception:
        return ""
    return ""


def _extract_searchable_text(filename: str, content: bytes) -> tuple[str, bool]:
    suffix = PurePosixPath(filename).suffix.casefold()
    try:
        if suffix == ".pdf":
            with pdfplumber.open(BytesIO(content)) as pdf:
                text = " ".join(
                    page.extract_text() or ""
                    for page in pdf.pages
                )
            if len(text.strip()) >= 80:
                return text, False
            ocr_text = _ocr_document(filename, content)
            return ocr_text or text, bool(ocr_text)
        if suffix == ".docx":
            document = Document(BytesIO(content))
            return (
                " ".join(paragraph.text for paragraph in document.paragraphs),
                False,
            )
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            ocr_text = _ocr_document(filename, content)
            return ocr_text, bool(ocr_text)
    except Exception:
        return "", False
    return "", False


def _detect_validity(filename: str, text: str) -> dict:
    source = f"{filename}\n{text}"
    patterns = (
        r"(?i)(?:validade|v[aá]lid[ao]\s+at[eé]|vencimento|val\.?)"
        r"[^0-9]{0,35}([0-3]?\d[./-][01]?\d[./-](?:20)?\d{2})",
        r"(?i)(?:vence(?:r[aá])?\s+em)[^0-9]{0,20}"
        r"([0-3]?\d[./-][01]?\d[./-](?:20)?\d{2})",
    )
    candidates = []
    for pattern in patterns:
        candidates.extend(re.findall(pattern, source))
    parsed = []
    for value in candidates:
        normalized = value.replace(".", "/").replace("-", "/")
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                parsed.append(datetime.strptime(normalized, fmt).date())
                break
            except ValueError:
                continue
    if not parsed:
        return {"validity_date": "", "validity_status": "Não identificada"}
    validity = max(parsed)
    days = (validity - date.today()).days
    if days < 0:
        status = "Vencido"
    elif days <= 30:
        status = "Vence em até 30 dias"
    else:
        status = "Válido"
    return {
        "validity_date": validity.strftime("%d/%m/%Y"),
        "validity_status": status,
    }


def _parse_winners_report(reference_file: tuple[str, bytes] | None) -> list[dict]:
    if not reference_file:
        return []
    filename, content = reference_file
    if PurePosixPath(filename).suffix.casefold() != ".pdf":
        return []
    try:
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return parse_vencedores_pdf_text(text)
    except Exception:
        return []


def _supplier_key(value: str) -> str:
    normalized = normalize_text(value)
    normalized = re.sub(
        r"\b(ltda|eireli|epp|me|sa|comercio|comercial|distribuidora)\b",
        " ",
        normalized,
    )
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def _winner_for_supplier(supplier: str, winners: list[dict]) -> dict | None:
    supplier_key = _supplier_key(supplier)
    supplier_tokens = [token for token in supplier_key.split() if len(token) >= 3]
    best_match = None
    best_score = 0
    for winner in winners:
        winner_key = _supplier_key(winner.get("nome", ""))
        winner_tokens = {token for token in winner_key.split() if len(token) >= 3}
        score = sum(token in winner_tokens for token in supplier_tokens)
        if (
            supplier_key
            and winner_key
            and (supplier_key in winner_key or winner_key in supplier_key)
        ):
            score += 3
        if score > best_score:
            best_match = winner
            best_score = score
    return best_match if best_score >= 1 else None


def _required_technical_documents(description: str) -> list[tuple[str, str]]:
    normalized = normalize_text(description)
    if not normalized:
        return []
    required = []
    seen = set()
    for code, label, category, keywords in DOCUMENT_RULES:
        if category != "TÉCNICOS" or code == "7.0.4":
            continue
        keyword_match = any(
            normalize_text(keyword) in normalized for keyword in keywords
        )
        if label == "AFE ANVISA" and re.search(r"\bafe\b", normalized):
            keyword_match = True
        if label == "Alvará Sanitário":
            keyword_match = keyword_match or (
                "alvara" in normalized and "sanitari" in normalized
            )
        if label == "Licença Sanitária":
            keyword_match = keyword_match or (
                "licenca" in normalized and "sanitari" in normalized
            )
        if keyword_match and (code, label) not in seen:
            required.append((code, label))
            seen.add((code, label))
    return required


def _filter_catalog_pdf(content: bytes, winner_items: list[dict]) -> tuple[bytes, int]:
    if not winner_items:
        return content, 0
    try:
        reader = PdfReader(BytesIO(content))
        selected_pages = []
        for page in reader.pages:
            page_text = normalize_text(page.extract_text() or "")
            page_selected = False
            for item in winner_items:
                item_number = str(item.get("item") or "").lstrip("0") or "0"
                code = str(item.get("codigo") or "")
                item_pattern = rf"\bitem\s*(?:n[ºo°.]?\s*)?0*{re.escape(item_number)}\b"
                description = normalize_text(
                    " ".join(
                        str(item.get(field) or "")
                        for field in ("descricao", "marca", "modelo")
                    )
                )
                keywords = {
                    word
                    for word in re.findall(r"[a-z0-9]{5,}", description)
                    if word
                    not in {
                        "marca",
                        "modelo",
                        "unidade",
                        "produto",
                        "quantidade",
                    }
                }
                keyword_hits = sum(
                    keyword in page_text for keyword in list(keywords)[:12]
                )
                if (
                    re.search(item_pattern, page_text)
                    or (code and re.search(rf"\b{re.escape(code)}\b", page_text))
                    or keyword_hits >= 2
                ):
                    page_selected = True
                    break
            if page_selected:
                selected_pages.append(page)

        if not selected_pages:
            return content, 0
        writer = PdfWriter()
        for page in selected_pages:
            writer.add_page(page)
        output = BytesIO()
        writer.write(output)
        return output.getvalue(), len(selected_pages)
    except Exception:
        return content, 0


def _merge_pdf_documents(contents: list[bytes]) -> bytes:
    if len(contents) == 1:
        return contents[0]
    writer = PdfWriter()
    try:
        for content in contents:
            reader = PdfReader(BytesIO(content))
            for page in reader.pages:
                writer.add_page(page)
        output = BytesIO()
        writer.write(output)
        return output.getvalue()
    except Exception:
        return contents[0]


def build_print_pdf(
    content: bytes,
    analysis: dict,
    selected_sources: list[str],
) -> tuple[bytes, int, int]:
    selected = set(selected_sources)
    if not selected:
        raise ValueError("Selecione pelo menos um documento para imprimir.")

    document_map = {
        document["source"]: document for document in analysis["documents"]
    }
    extracted_entries = _extract_package_documents(
        content,
        analysis.get("package_name", ""),
    )
    writer = PdfWriter()
    document_count = 0
    page_count = 0

    for entry in extracted_entries:
        source = entry["source"]
        if source not in selected or source not in document_map:
            continue
        document = document_map[source]
        if document["extension"] != ".pdf":
            continue
        payload = entry["content"]
        if document["document_code"] == "7.0.4":
            payload, _ = _filter_catalog_pdf(
                payload,
                document.get("winner_items", []),
            )
        try:
            reader = PdfReader(BytesIO(payload))
            for page in reader.pages:
                writer.add_page(page)
                page_count += 1
            document_count += 1
        except Exception:
            continue

    if not page_count:
        raise ValueError(
            "Nenhum PDF válido foi encontrado entre os documentos selecionados."
        )
    output = BytesIO()
    writer.write(output)
    return output.getvalue(), document_count, page_count


def get_selected_pdf_documents(
    content: bytes,
    analysis: dict,
    selected_sources: list[str],
) -> list[dict]:
    selected = set(selected_sources)
    document_map = {
        document["source"]: document for document in analysis["documents"]
    }
    extracted_entries = _extract_package_documents(
        content,
        analysis.get("package_name", ""),
    )
    results = []
    used_names: dict[str, int] = {}
    for entry in extracted_entries:
        source = entry["source"]
        if source not in selected or source not in document_map:
            continue
        document = document_map[source]
        if document["extension"] != ".pdf":
            continue
        payload = entry["content"]
        if document["document_code"] == "7.0.4":
            payload, _ = _filter_catalog_pdf(
                payload,
                document.get("winner_items", []),
            )
        try:
            PdfReader(BytesIO(payload))
        except Exception:
            continue
        desired_name = document["standardized_name"]
        key = desired_name.casefold()
        used_names[key] = used_names.get(key, 0) + 1
        if used_names[key] > 1:
            path = PurePosixPath(desired_name)
            desired_name = (
                f"{path.stem} ({used_names[key]}){path.suffix}"
            )
        results.append(
            {
                "name": desired_name,
                "content": payload,
            }
        )
    if not results:
        raise ValueError(
            "Nenhum PDF válido foi encontrado entre os documentos selecionados."
        )
    return results


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
            if entry.filename.casefold().endswith(
                (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")
            ):
                try:
                    extracted.extend(
                        _extract_all_tar_documents(
                            payload,
                            prefix=source,
                            depth=depth + 1,
                            limits=limits,
                        )
                    )
                    continue
                except tarfile.ReadError:
                    pass
            if entry.filename.casefold().endswith(".rar"):
                try:
                    extracted.extend(
                        _extract_all_rar_documents(
                            payload,
                            prefix=source,
                            limits=limits,
                        )
                    )
                    continue
                except Exception:
                    pass

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


def _extract_all_tar_documents(
    content: bytes,
    *,
    prefix: str,
    depth: int,
    limits: dict,
) -> list[dict]:
    if depth > MAX_NESTED_ZIP_DEPTH:
        raise ValueError(
            f"O pacote contém mais de {MAX_NESTED_ZIP_DEPTH} níveis de arquivos."
        )

    extracted = []
    with tarfile.open(fileobj=BytesIO(content), mode="r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            stream = archive.extractfile(member)
            if stream is None:
                continue
            payload = stream.read()
            source = f"{prefix}/{member.name}".strip("/")
            lowered = member.name.casefold()

            if lowered.endswith(".zip"):
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
                except ValueError as exc:
                    if "não é um ZIP válido" not in str(exc):
                        raise
            if lowered.endswith(
                (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")
            ):
                try:
                    extracted.extend(
                        _extract_all_tar_documents(
                            payload,
                            prefix=source,
                            depth=depth + 1,
                            limits=limits,
                        )
                    )
                    continue
                except tarfile.ReadError:
                    pass
            if lowered.endswith(".rar"):
                try:
                    extracted.extend(
                        _extract_all_rar_documents(
                            payload,
                            prefix=source,
                            limits=limits,
                        )
                    )
                    continue
                except Exception:
                    pass

            limits["files"] += 1
            limits["bytes"] += len(payload)
            if limits["files"] > MAX_FILES:
                raise ValueError(
                    f"O pacote excede o limite de {MAX_FILES} arquivos."
                )
            if limits["bytes"] > MAX_UNCOMPRESSED_BYTES:
                raise ValueError(
                    "O conteúdo descompactado excede o limite de 300 MB."
                )
            extracted.append({"source": source, "content": payload})
    return extracted


def _extract_all_rar_documents(
    content: bytes,
    *,
    prefix: str,
    limits: dict,
) -> list[dict]:
    import rarfile

    extracted = []
    with rarfile.RarFile(BytesIO(content)) as archive:
        for info in archive.infolist():
            if info.isdir():
                continue
            payload = archive.read(info)
            limits["files"] += 1
            limits["bytes"] += len(payload)
            if limits["files"] > MAX_FILES:
                raise ValueError(
                    f"O pacote excede o limite de {MAX_FILES} arquivos."
                )
            if limits["bytes"] > MAX_UNCOMPRESSED_BYTES:
                raise ValueError(
                    "O conteúdo descompactado excede o limite de 300 MB."
                )
            extracted.append(
                {
                    "source": f"{prefix}/{info.filename}".strip("/"),
                    "content": payload,
                }
            )
    return extracted


def _extract_package_documents(content: bytes, package_name: str = "") -> list[dict]:
    lowered = package_name.casefold()
    limits = {"files": 0, "bytes": 0}
    if lowered.endswith(".rar"):
        try:
            return _extract_all_rar_documents(
                content,
                prefix="",
                limits=limits,
            )
        except Exception as exc:
            raise ValueError(
                "Não foi possível abrir o RAR. Verifique se o arquivo está íntegro."
            ) from exc
    if lowered.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")):
        try:
            return _extract_all_tar_documents(
                content,
                prefix="",
                depth=0,
                limits=limits,
            )
        except tarfile.ReadError as exc:
            raise ValueError("O arquivo TAR enviado não é válido.") from exc
    return _extract_all_zip_documents(content)


def _safe_basename(name: str) -> str:
    basename = PurePosixPath(name.replace("\\", "/")).name
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", basename).strip(" .")
    return cleaned or "documento_sem_nome"


def supplier_label_from_package(filename: str) -> str:
    digits = re.sub(r"\D", "", PurePosixPath(filename).stem)
    if len(digits) >= 14:
        cnpj = digits[-14:]
        return (
            f"Fornecedor - {cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/"
            f"{cnpj[8:12]}-{cnpj[12:]}"
        )
    cleaned = re.sub(
        r"(?i)^documentos?fornecedor(?:nalicitacao)?[-_ ]*",
        "",
        PurePosixPath(filename).stem,
    ).strip(" -_")
    return cleaned or "FORNECEDOR_NAO_IDENTIFICADO"


def _supplier_from_source(
    source: str,
    winners: list[dict] | None = None,
    default_supplier: str = "",
) -> str:
    parts = [
        part
        for part in source.replace("\\", "/").split("/")
        if part and part not in {".", ".."}
    ]
    if len(parts) < 2:
        default_digits = re.sub(r"\D", "", default_supplier)
        if winners and len(default_digits) >= 14:
            cnpj = default_digits[-14:]
            for winner in winners:
                if re.sub(r"\D", "", winner.get("cnpj", "")) == cnpj:
                    return re.sub(
                        r'[<>:"/\\|?*\x00-\x1f]',
                        "_",
                        winner.get("nome", default_supplier),
                    ).strip(" .")
        return default_supplier or "FORNECEDOR_NAO_IDENTIFICADO"
    if winners:
        for part in parts[:-1]:
            winner = _winner_for_supplier(PurePosixPath(part).stem, winners)
            if winner:
                return re.sub(
                    r'[<>:"/\\|?*\x00-\x1f]',
                    "_",
                    winner.get("nome", PurePosixPath(part).stem),
                ).strip(" .")
    first_stem = PurePosixPath(parts[0]).stem
    generic_container = normalize_text(first_stem) in {
        "habilitacao",
        "documentos",
        "rms e cat",
        "rms cat",
        "arquivos",
        "anexos",
    }
    if default_supplier and generic_container:
        return default_supplier
    supplier_part = (
        first_stem
        if PurePosixPath(parts[0]).suffix.casefold()
        in {".zip", ".tar", ".tgz", ".gz", ".bz2"}
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
    reference_file: tuple[str, bytes] | None = None,
    default_supplier: str = "",
    package_name: str = "",
) -> dict:
    if profile not in PROFILE_CHECKLISTS:
        raise ValueError(f"Perfil documental inválido: {profile}")

    entries = _extract_package_documents(content, package_name)
    winners = _parse_winners_report(reference_file)
    documents = []
    for entry in entries:
        filename = _safe_basename(entry["source"])
        suffix = PurePosixPath(filename).suffix.casefold()
        searchable_text, ocr_used = _extract_searchable_text(
            filename,
            entry["content"],
        )
        identification = identify_document(filename, searchable_text)
        validity = _detect_validity(filename, searchable_text)
        supplier = _supplier_from_source(
            entry["source"],
            winners,
            default_supplier,
        )
        winner = _winner_for_supplier(supplier, winners)
        standardized_name = (
            f"{identification['code']} - {identification['label']}{suffix}"
            if identification
            else filename
        )
        if identification and identification["code"] == "10.9.3":
            normalized_filename = normalize_text(filename)
            item_match = re.search(
                r"lote[\s_\-\[\]]*0*(\d{1,4})",
                normalized_filename,
            ) or re.search(
                r"item[\s_\-\[\]]*0*(\d{1,4})",
                normalized_filename,
            )
            if item_match:
                standardized_name = (
                    f"10.9.3 - Registro ANVISA - Item "
                    f"{int(item_match.group(1))}{suffix}"
                )
        documents.append(
            {
                "source": entry["source"],
                "supplier": supplier,
                "name": filename,
                "standardized_name": standardized_name,
                "identified": identification is not None,
                "document_code": identification["code"] if identification else "",
                "document_label": identification["label"] if identification else "",
                "identification_confidence": (
                    identification["confidence"] if identification else 0
                ),
                "identified_by": (
                    identification["identified_by"] if identification else ""
                ),
                "category": (
                    identification["category"]
                    if identification
                    else "NÃO CLASSIFICADOS"
                ),
                "extension": suffix or "sem extensão",
                "size": len(entry["content"]),
                "ocr_candidate": suffix
                in {".png", ".jpg", ".jpeg", ".tif", ".tiff"},
                "ocr_used": ocr_used,
                **validity,
                "winner_items": winner.get("itens", []) if winner else [],
            }
        )

    required_technical = set(
        _required_technical_documents(technical_qualification)
    )
    required_groups: dict[tuple[str, str, str], list[dict]] = {}
    for document in documents:
        if not document["identified"]:
            document["selected_for_requirement"] = False
            continue
        requirement = (document["document_code"], document["document_label"])
        is_required = (
            document["document_code"] in STANDARD_REQUIRED_CODES
            or document["document_code"] in CONDITIONAL_DOCUMENT_CODES
            or requirement in required_technical
        )
        document["selected_for_requirement"] = False
        if is_required:
            key = (
                document["supplier"],
                document["document_code"],
                document["document_label"],
            )
            required_groups.setdefault(key, []).append(document)

    for candidates in required_groups.values():
        best_confidence = max(
            document["identification_confidence"] for document in candidates
        )
        best_candidates = [
            document
            for document in candidates
            if document["identification_confidence"] == best_confidence
        ]
        code = candidates[0]["document_code"]
        if code in MULTIPLE_DOCUMENT_CODES or code == "7.0.4":
            selected = best_candidates
        else:
            selected = [max(best_candidates, key=lambda document: document["size"])]
        for document in selected:
            document["selected_for_requirement"] = True

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
        "winners_identified": len(winners),
        "checklist": checklist,
        "totals": totals,
        "ocr_candidates": sum(document["ocr_candidate"] for document in documents),
        "ocr_processed": sum(document["ocr_used"] for document in documents),
        "package_name": package_name,
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
    extracted_entries = _extract_package_documents(
        content,
        analysis.get("package_name", ""),
    )

    with ZipFile(output_buffer, "w", ZIP_DEFLATED) as target:
        output_names: dict[str, int] = {}
        catalog_groups: dict[str, list[bytes]] = {}
        for entry in extracted_entries:
            if entry["source"] not in document_map:
                continue
            document = document_map[entry["source"]]
            payload = entry["content"]
            if (
                document["selected_for_requirement"]
                and document["document_code"] == "7.0.4"
            ):
                payload, selected_pages = _filter_catalog_pdf(
                    payload,
                    document.get("winner_items", []),
                )
                document["catalog_pages_selected"] = selected_pages
                catalog_groups.setdefault(document["supplier"], []).append(payload)
                continue

            if document["selected_for_requirement"]:
                folder = (
                    f"{document['supplier']}/01 - Documentos Exigidos"
                )
                desired_name = document["standardized_name"]
            elif document["identified"]:
                folder = (
                    f"{document['supplier']}/02 - Documentos Não Utilizados"
                )
                desired_name = document["name"]
            else:
                folder = (
                    f"{document['supplier']}/03 - Documentos Não Identificados"
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
                payload,
            )

        for supplier, catalog_contents in catalog_groups.items():
            target.writestr(
                (
                    f"{supplier}/01 - Documentos Exigidos/"
                    "7.0.4 - Catálogo Itens Vencedores.pdf"
                ),
                _merge_pdf_documents(catalog_contents),
            )

        report = StringIO()
        writer = csv.writer(report, delimiter=";")
        writer.writerow(
            [
                "arquivo_original",
                "arquivo_renomeado",
                "fornecedor",
                "identificado",
                "utilizado",
                "identificado_por",
                "confianca",
                "codigo",
                "categoria",
                "extensao",
                "tamanho_bytes",
                "ocr",
                "validade",
                "situacao_validade",
            ]
        )
        for document in analysis["documents"]:
            writer.writerow(
                [
                    document["name"],
                    document["standardized_name"],
                    document["supplier"],
                    "sim" if document["identified"] else "não",
                    "sim" if document["selected_for_requirement"] else "não",
                    document["identified_by"],
                    document["identification_confidence"],
                    document["document_code"],
                    document["category"],
                    document["extension"],
                    document["size"],
                    "sim" if document["ocr_used"] else "não",
                    document["validity_date"],
                    document["validity_status"],
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
                if document["selected_for_requirement"]
            }
            located_code_labels = {
                (document["document_code"], document["document_label"])
                for document in supplier_documents
                if document["selected_for_requirement"]
            }
            required_technical = _required_technical_documents(
                analysis.get("technical_qualification", "")
            )
            validity_alerts = [
                document
                for document in supplier_documents
                if document["selected_for_requirement"]
                and document["validity_status"]
                in {"Vencido", "Vence em até 30 dias"}
            ]
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
                    if document["selected_for_requirement"]
                ],
                "",
                "DOCUMENTOS PADRÃO NÃO LOCALIZADOS:",
                *[
                    f"[  ] {code} - {label}"
                    for code, label, category, _ in DOCUMENT_RULES
                    if (
                        code in STANDARD_REQUIRED_CODES
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
                "",
                "QUALIFICAÇÃO TÉCNICA NÃO LOCALIZADA:",
                *(
                    [
                        f"[  ] {code} - {label}"
                        for code, label in required_technical
                        if (code, label) not in located_code_labels
                    ]
                    or ["Nenhuma pendência técnica identificada."]
                ),
                "",
                "ALERTAS DE VALIDADE:",
                *(
                    [
                        f"[!] {document['standardized_name']} — "
                        f"{document['validity_status']} "
                        f"({document['validity_date']})"
                        for document in validity_alerts
                    ]
                    or ["Nenhum vencimento identificado."]
                ),
            ]
            target.writestr(
                f"{supplier}/RELATÓRIO DE CONFERÊNCIA.txt",
                "\n".join(supplier_lines).encode("utf-8"),
            )
            pdf_report = _build_report_pdf(supplier_lines)
            if pdf_report:
                target.writestr(
                    f"{supplier}/RELATÓRIO DE CONFERÊNCIA.pdf",
                    pdf_report,
                )

    return output_buffer.getvalue()


def _build_report_pdf(lines: list[str]) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=1.7 * cm,
            leftMargin=1.7 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph("RELATÓRIO DE CONFERÊNCIA DOCUMENTAL", styles["Title"]),
            Spacer(1, 10),
        ]
        for line in lines:
            if not line:
                story.append(Spacer(1, 7))
            elif line.endswith(":"):
                story.append(Paragraph(line, styles["Heading3"]))
            else:
                safe_line = (
                    line.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                story.append(Paragraph(safe_line, styles["BodyText"]))
        document.build(story)
        return output.getvalue()
    except Exception:
        return b""
