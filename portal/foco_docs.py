from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path, PurePosixPath
import csv
from datetime import date, datetime
import shutil
import subprocess
import re
import tarfile
import tempfile
import unicodedata
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import pdfplumber
from docx import Document
from pypdf import PdfReader, PdfWriter

from licitasuite.parsers.vencedores_pdf_robusto import parse_vencedores_pdf_text


TCU_CERTIDOES_URL = "https://certidoes-apf.apps.tcu.gov.br/"
MAX_FILES = 2_000
MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024
MAX_NESTED_ZIP_DEPTH = 4
CONDITIONAL_DOCUMENT_CODES = {"10.6.2", "10.6.3", "10.6.4"}
STANDARD_REQUIRED_CODES = {
    "7.0.1",
    "7.0.2",
    "7.0.3",
    "7.0.4",
    "10.6.1",
    "10.7.1",
    "10.7.2",
    "10.7.3",
    "10.7.4",
    "10.7.5",
    "10.7.6",
    "10.8.1",
}
MULTIPLE_DOCUMENT_CODES = {"10.6.1", "10.9.3"}
INTERNAL_VALIDITY_CODES = {
    "10.7.1",
    "10.7.2",
    "10.7.3",
    "10.7.4",
    "10.7.5",
    "10.7.6",
    "10.8.1",
}

DOCUMENT_RULES = (
    (
        "7.0.1",
        "SICAF CRC CAGEF",
        "BÁSICOS",
        ("sicaf", "crc", "cagef", "registro cadastral"),
    ),
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
        "10.6.1",
        "Ato Constitutivo e Contrato Social",
        "BÁSICOS",
        ("contrato social", "estatuto", "ato constitutivo", "alteracao contratual", "alterao contratual"),
    ),
    (
        "10.6.2",
        "Procuração e Documento do Representante",
        "BÁSICOS",
        ("procuracao", "procuração", "procurao", "representante", "rg cpf"),
    ),
    (
        "10.6.3",
        "Autorização de Empresa Estrangeira",
        "BÁSICOS",
        ("empresa estrangeira", "autorizacao funcionamento estrangeira"),
    ),
    (
        "10.6.4",
        "Certidão Simplificada ME EPP",
        "BÁSICOS",
        (
            "certidao simplificada",
            "certidão simplificada",
            "me epp",
            "microempresa",
            "empresa de pequeno porte",
        ),
    ),
    ("10.7.1", "Comprovante de CNPJ", "BÁSICOS", ("cnpj",)),
    (
        "10.7.2",
        "Certidão Federal e Seguridade Social",
        "BÁSICOS",
        (
            "certidao federal",
            "certidão federal",
            "receita federal",
            "cnd federal",
            "cnd unificada",
            "positiva com efeito de negativa federal",
        ),
    ),
    (
        "10.7.3",
        "Certidão Estadual",
        "BÁSICOS",
        (
            "certidao estadual",
            "certidão estadual",
            "fazenda estadual",
            "cnd estadual",
            "positiva com efeito de negativa estadual",
        ),
    ),
    (
        "10.7.4",
        "Certidão Municipal",
        "BÁSICOS",
        (
            "certidao municipal",
            "certidão municipal",
            "fazenda municipal",
            "cnd municipal",
            "debitos municipais",
            "débitos municipais",
            "tributos municipais",
            "secretaria municipal",
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
    ("10.7.5", "FGTS", "BÁSICOS", ("fgts", "crf caixa", "regularidade do fgts")),
    (
        "10.7.6",
        "Certidão Negativa de Débitos Trabalhistas",
        "BÁSICOS",
        (
            "cndt",
            "debitos trabalhistas",
            "débitos trabalhistas",
            "cnd trabalhista",
            "positiva com efeito de negativa trabalhista",
        ),
    ),
    (
        "10.8.1",
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
        (
            "licenca sanitaria",
            "licença sanitária",
            "licenca de funcionamento",
            "lic func",
            "lic. func",
            "alvara est",
            "alvará est",
        ),
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
            "ae anvisa",
            "aut func",
            "aut. func",
            "aut func federal",
            "alv. fed",
            "alv fed",
        ),
    ),
    (
        "10.9.3",
        "Registro ANVISA",
        "TÉCNICOS",
        (
            "registro anvisa",
            "registro do produto",
            "registos",
            "registros_bulas",
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
        "SICAF CRC CAGEF",
        "BÁSICOS",
        (
            ("sistema de cadastramento unificado de fornecedores",),
            ("certificado de registro cadastral",),
            ("cagef", "seplag"),
        ),
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
        "10.6.1",
        "Ato Constitutivo e Contrato Social",
        "BÁSICOS",
        (
            ("contrato social",),
            ("alteracao contratual",),
            ("alterao contratual",),
            ("ato constitutivo",),
        ),
    ),
    (
        "10.6.2",
        "Procuração e Documento do Representante",
        "BÁSICOS",
        (
            ("instrumento de procuracao",),
            ("instrumento particular de procura",),
            ("procurao",),
            ("outorgante", "outorgado"),
        ),
    ),
    (
        "10.6.3",
        "Autorização de Empresa Estrangeira",
        "BÁSICOS",
        (("decreto de autorizacao", "empresa estrangeira"),),
    ),
    (
        "10.6.4",
        "Certidão Simplificada ME EPP",
        "BÁSICOS",
        (
            ("certidao simplificada",),
        ),
    ),
    (
        "10.7.1",
        "Comprovante de CNPJ",
        "BÁSICOS",
        (("comprovante de inscricao e de situacao cadastral",),),
    ),
    (
        "10.7.2",
        "Certidão Federal e Seguridade Social",
        "BÁSICOS",
        (
            ("debitos relativos a creditos tributarios federais",),
            ("divida ativa da uniao", "certidao"),
            ("receita federal", "positiva com efeito de negativa"),
            ("procuradoria-geral da fazenda nacional", "positiva com efeito de negativa"),
            ("tributos federais", "positiva com efeito de negativa"),
            ("creditos tributarios federais", "efeito de negativa"),
            ("divida ativa da uniao", "efeito de negativa"),
        ),
    ),
    (
        "10.7.3",
        "Certidão Estadual",
        "BÁSICOS",
        (
            ("certidao", "fazenda estadual"),
            ("certidao", "secretaria de estado da fazenda"),
            ("fazenda estadual", "positiva com efeito de negativa"),
            ("secretaria de estado da fazenda", "efeito de negativa"),
            ("debitos estaduais", "efeito de negativa"),
            ("tributos estaduais", "certidao"),
        ),
    ),
    (
        "10.7.4",
        "Certidão Municipal",
        "BÁSICOS",
        (
            ("certidao", "debitos municipais"),
            ("certidao", "débitos municipais"),
            ("certidao", "fazenda municipal"),
            ("certidao mobiliaria",),
            ("municipio de", "certidao positiva com efeito de negativa"),
            ("município de", "certidão positiva com efeito de negativa"),
            ("fazenda municipal", "certidao positiva com efeito de negativa"),
            ("fazenda municipal", "efeito de negativa"),
            ("debitos municipais", "efeito de negativa"),
            ("débitos municipais", "efeito de negativa"),
            ("tributos municipais", "certidao"),
            ("secretaria municipal", "certidao"),
            ("inscricao empresa", "fazenda municipal"),
            ("inscrição empresa", "fazenda municipal"),
        ),
    ),
    (
        "10.7.5",
        "FGTS",
        "BÁSICOS",
        (("certificado de regularidade do fgts",), ("regularidade do fgts", "caixa")),
    ),
    (
        "10.7.6",
        "Certidão Negativa de Débitos Trabalhistas",
        "BÁSICOS",
        (
            ("certidao negativa de debitos trabalhistas",),
            ("certidao positiva de debitos trabalhistas", "efeito de negativa"),
            ("debitos trabalhistas", "efeito de negativa"),
            ("trabalhistas", "efeito de negativa"),
            ("justica do trabalho", "positiva com efeito de negativa"),
        ),
    ),
    (
        "10.8.1",
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
        (
            ("autorizacao de funcionamento", "anvisa"),
            ("autorizao de funcionamento", "anvisa"),
        ),
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

CHECKLIST_CODE_MAP = {
    "sicaf": {"7.0.1"},
    "proposta comercial": {"7.0.2"},
    "requerimento": {"7.0.3"},
    "catalogo dos itens vencedores": {"7.0.4"},
    "contrato social": {"10.6.1"},
    "ato constitutivo": {"10.6.1"},
    "cnpj": {"10.7.1"},
    "certidao federal": {"10.7.2"},
    "certidao estadual": {"10.7.3"},
    "certidao municipal": {"10.7.4"},
    "fgts": {"10.7.5"},
    "cndt": {"10.7.6"},
    "certidao de falencia": {"10.8.1"},
    "regularidade fiscal": {"10.7.1", "10.7.2", "10.7.3", "10.7.4", "10.7.5"},
    "regularidade trabalhista": {"10.7.6"},
    "qualificacao tecnica": {"10.9", "10.9.1", "10.9.2", "10.9.3", "10.9.5"},
    "licenca sanitaria": {"10.9.1"},
    "afe/anvisa": {"10.9.2"},
    "responsavel tecnico": {"10.9"},
    "conselho profissional": {"10.9"},
    "atestado de capacidade": {"10.9"},
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
    skip_contract_from_content = (
        "alvara" in normalized
        and ("local" in normalized or "func" in normalized)
        and "sanitari" not in normalized
    )
    for code, label, category, keywords in DOCUMENT_RULES:
        keyword_match = any(
            normalize_text(keyword).strip() in normalized for keyword in keywords
        )
        if label == "Registro ANVISA" and "bula" in normalized:
            keyword_match = False
        if label == "AFE ANVISA":
            keyword_match = keyword_match or (
                re.search(r"\b(?:afe|ae)\b", normalized) is not None
                and (
                    "anvisa" in normalized
                    or "dou" in normalized
                    or "autorizacao" in normalized
                    or "autorizao" in normalized
                )
            )
        if label == "Registro ANVISA":
            keyword_match = keyword_match or (
                re.search(r"\bregistro\b", normalized) is not None
                and "registro cadastral" not in normalized
                and "contrato" not in normalized
                and "junta comercial" not in normalized
            )
        if keyword_match:
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
        if skip_contract_from_content and code == "10.6.1":
            continue
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


def _identify_document_by_content(extracted_text: str) -> dict | None:
    normalized_content = normalize_text(extracted_text)
    if not normalized_content:
        return None
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
                "identified_by": "conteúdo da página",
            }
    return None


def _identification_from_split_filename(filename: str) -> dict | None:
    match = re.search(
        r" - páginas? .+? - (?P<code>\d+(?:\.\d+)*) - (?P<label>.+)\.pdf$",
        filename,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    code = match.group("code")
    label = match.group("label").strip()
    category = next(
        (
            rule_category
            for rule_code, _, rule_category, _ in DOCUMENT_RULES
            if rule_code == code
        ),
        "BÁSICOS",
    )
    return {
        "code": code,
        "label": label,
        "category": category,
        "confidence": 90,
        "identified_by": "páginas separadas do PDF",
    }


def document_group(code: str) -> str:
    if code.startswith("7.0"):
        return "Documentos iniciais"
    if code.startswith("10.6"):
        return "Habilitação jurídica"
    if code == "10.7.6":
        return "Regularidade trabalhista"
    if code.startswith("10.7"):
        return "Regularidade fiscal"
    if code.startswith("10.8"):
        return "Qualificação econômico-financeira"
    if code.startswith("10.9"):
        return "Qualificação técnica"
    return "Outros documentos"


def _document_order(code: str) -> tuple[int, int, str]:
    ordered_codes = {
        "7.0.1": (3, 1),  # SICAF/CRC/CAGEF antes das certidões
        "10.6.1": (3, 2),
        "10.6.2": (3, 3),
        "10.6.3": (3, 4),
        "10.6.4": (3, 5),
        "10.7.1": (3, 6),
        "10.7.2": (3, 7),
        "10.7.3": (3, 8),
        "10.7.4": (3, 9),
        "10.7.5": (3, 10),
        "10.7.6": (3, 11),
        "10.8.1": (3, 12),
        "10.9": (4, 1),
        "10.9.1": (4, 2),
        "10.9.2": (4, 3),
        "10.9.3": (4, 4),
        "10.9.5": (4, 5),
        "7.0.2": (5, 1),  # proposta depois da habilitação/técnica
        "7.0.4": (5, 2),
        "7.0.3": (5, 3),
    }
    stage, order = ordered_codes.get(code, (9, 99))
    return stage, order, code


def _organized_folder(document: dict) -> str:
    code = document["document_code"]
    supplier = document["supplier"]
    if code == "7.0.1" or code.startswith(("10.6", "10.7", "10.8")):
        return f"{supplier}/03 - Documentos de Habilitação"
    if code.startswith("10.9"):
        return f"{supplier}/04 - Qualificação Técnica"
    if code in {"7.0.2", "7.0.3", "7.0.4"}:
        return f"{supplier}/05 - Proposta e Itens Vencedores"
    return f"{supplier}/03 - Documentos de Habilitação"


def _official_url_from_document(text: str) -> str:
    candidates = re.findall(
        r"(?i)\b(?:https?://|www\.)[^\s<>{}\[\]\"']+",
        text or "",
    )
    for candidate in candidates:
        url = candidate.rstrip(".,;:)")
        if url.casefold().startswith("www."):
            url = f"https://{url}"
        lowered = url.casefold()
        if any(
            official_domain in lowered
            for official_domain in (
                ".gov.br",
                ".jus.br",
                "caixa.gov.br",
                "tst.jus.br",
            )
        ):
            return url
    return ""


def _validation_data_text(
    *,
    cnpj: str = "",
    validity_date: str = "",
) -> str:
    parts = []
    formatted_cnpj = _format_cnpj(cnpj)
    if formatted_cnpj:
        parts.append(f"CNPJ: {formatted_cnpj}")
    if validity_date:
        parts.append(f"Validade: {validity_date}")
    return " | ".join(parts)


def document_validation(
    code: str,
    document_text: str = "",
    *,
    supplier_cnpj: str = "",
    validity_date: str = "",
) -> tuple[str, str, str]:
    validation_data = _validation_data_text(
        cnpj=supplier_cnpj or _extract_cnpj(document_text),
        validity_date=validity_date,
    )
    extracted_url = _official_url_from_document(document_text)
    if extracted_url:
        note = "Endereço oficial de autenticação localizado no documento."
        if validation_data:
            note = f"{note} Dados: {validation_data}."
        return extracted_url, note, validation_data

    official_links = {
        "7.0.1": (
            "https://www.gov.br/compras/pt-br/sicaf-digital",
            "Consulta no SICAF/Compras.gov.br.",
        ),
        "10.7.1": (
            "https://solucoes.receita.fazenda.gov.br/Servicos/"
            "cnpjreva/Cnpjreva_S.aspx",
            "Consulta cadastral na Receita Federal.",
        ),
        "10.7.2": (
            "https://servicos.receita.fazenda.gov.br/servicos/certidao/",
            "Consulta e autenticação na Receita Federal/PGFN.",
        ),
        "10.7.5": (
            "https://consulta-crf.caixa.gov.br/consultacrf/pages/"
            "consultaEmpregador.jsf",
            "Consulta do CRF no site da CAIXA.",
        ),
        "10.7.6": (
            "https://www.tst.jus.br/certidao1",
            "Emissão e validação da CNDT no TST.",
        ),
        "10.9.2": (
            "https://www.gov.br/anvisa/pt-br/sistemas/sistema-de-consultas",
            "Consulta pública de empresas e AFE na Anvisa.",
        ),
        "10.9.3": (
            "https://www.gov.br/anvisa/pt-br/sistemas/sistema-de-consultas",
            "Consulta pública do registro do produto na Anvisa.",
        ),
    }
    regional_notes = {
        "10.7.3": "Validar no portal da Secretaria da Fazenda do estado emissor.",
        "10.7.4": "Validar no portal da prefeitura/município emissor.",
        "10.8.1": "Validar no portal do Tribunal de Justiça emissor.",
        "10.9.1": "Validar na Vigilância Sanitária estadual ou municipal emissora.",
        "10.9": "Validar no conselho profissional que emitiu o certificado.",
    }
    regional_codes = {"10.7.3", "10.7.4", "10.8.1", "10.9.1", "10.9"}
    if code in official_links:
        url, note = official_links[code]
        if validation_data:
            note = f"{note} Dados para consulta: {validation_data}."
        return url, note, validation_data
    note = regional_notes.get(
        code,
        "Conferência documental sem consulta pública única.",
    )
    if validation_data:
        note = f"{note} Dados para consulta: {validation_data}."
    return "", note, validation_data


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


def _extract_searchable_text(
    filename: str,
    content: bytes,
    *,
    allow_ocr: bool = True,
) -> tuple[str, bool]:
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
            if not allow_ocr:
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
            if not allow_ocr:
                return "", False
            ocr_text = _ocr_document(filename, content)
            return ocr_text, bool(ocr_text)
    except Exception:
        return "", False
    return "", False


def _detect_validity(
    filename: str,
    text: str,
    *,
    reference_date: date | None = None,
) -> dict:
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
    reference = reference_date or date.today()
    days = (validity - reference).days
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


def _build_checklist(profile: str, documents: list[dict]) -> list[dict]:
    found_codes = {
        document["document_code"]
        for document in documents
        if document.get("identified") and document.get("document_code")
    }
    searchable_names = " ".join(
        f"{document.get('name', '')} {document.get('standardized_name', '')} "
        f"{document.get('document_label', '')}"
        for document in documents
    )
    normalized_names = normalize_text(searchable_names)
    checklist = []
    for label, keywords in PROFILE_CHECKLISTS[profile]:
        normalized_label = normalize_text(label)
        mapped_codes = CHECKLIST_CODE_MAP.get(normalized_label, set())
        found_by_code = bool(mapped_codes and mapped_codes.intersection(found_codes))
        found_by_text = any(
            normalize_text(keyword) in normalized_names for keyword in keywords
        )
        checklist.append(
            {
                "document": label,
                "status": "Localizado" if found_by_code or found_by_text else "Pendente",
            }
        )
    return checklist


def _filter_catalog_pdf(content: bytes, winner_items: list[dict]) -> tuple[bytes, list[int]]:
    if not winner_items:
        return content, []
    try:
        reader = PdfReader(BytesIO(content))
        selected_pages = []
        for page_number, page in enumerate(reader.pages, start=1):
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
                selected_pages.append((page_number, page))

        if not selected_pages:
            return content, []
        writer = PdfWriter()
        page_numbers = []
        for page_number, page in selected_pages:
            page_numbers.append(page_number)
            writer.add_page(page)
        output = BytesIO()
        writer.write(output)
        return output.getvalue(), page_numbers
    except Exception:
        return content, []


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


def _entries_from_analysis_or_package(content: bytes, analysis: dict) -> list[dict]:
    cached_entries = analysis.get("_entry_contents")
    if isinstance(cached_entries, dict) and cached_entries:
        return [
            {"source": source, "content": payload}
            for source, payload in cached_entries.items()
        ]
    return _extract_package_documents(
        content,
        analysis.get("package_name", ""),
        split_compound_pdfs=analysis.get("split_compound_pdfs", True),
        split_only_likely_documents=analysis.get("fast_mode", True),
    )


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
    extracted_entries = _entries_from_analysis_or_package(content, analysis)
    writer = PdfWriter()
    document_count = 0
    page_count = 0

    selected_entries = [
        entry
        for entry in extracted_entries
        if entry["source"] in selected and entry["source"] in document_map
    ]
    selected_entries.sort(
        key=lambda entry: (
            _document_order(document_map[entry["source"]]["document_code"]),
            document_map[entry["source"]]["standardized_name"],
        )
    )

    for entry in selected_entries:
        source = entry["source"]
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
    extracted_entries = _entries_from_analysis_or_package(content, analysis)
    results = []
    used_names: dict[str, int] = {}
    selected_entries = [
        entry
        for entry in extracted_entries
        if entry["source"] in selected and entry["source"] in document_map
    ]
    selected_entries.sort(
        key=lambda entry: (
            _document_order(document_map[entry["source"]]["document_code"]),
            document_map[entry["source"]]["standardized_name"],
        )
    )

    for entry in selected_entries:
        source = entry["source"]
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
                            depth=depth + 1,
                        )
                    )
                    continue
                except Exception as exc:
                    raise ValueError(
                        f"Não foi possível abrir o RAR interno: {source}."
                    ) from exc

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
                            depth=depth + 1,
                        )
                    )
                    continue
                except Exception as exc:
                    raise ValueError(
                        f"Não foi possível abrir o RAR interno: {source}."
                    ) from exc

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
    depth: int,
) -> list[dict]:
    if depth > MAX_NESTED_ZIP_DEPTH:
        raise ValueError(
            f"O pacote contém mais de {MAX_NESTED_ZIP_DEPTH} níveis de arquivos."
        )
    try:
        return _extract_rar_with_rarfile(
            content,
            prefix=prefix,
            limits=limits,
            depth=depth,
        )
    except Exception:
        return _extract_rar_with_external_tool(
            content,
            prefix=prefix,
            limits=limits,
            depth=depth,
        )


def _extract_nested_payload(
    *,
    payload: bytes,
    source: str,
    lowered: str,
    limits: dict,
    depth: int,
) -> list[dict] | None:
    if lowered.endswith(".zip"):
        return _extract_all_zip_documents(
            payload,
            prefix=source,
            depth=depth + 1,
            limits=limits,
        )
    if lowered.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")):
        return _extract_all_tar_documents(
            payload,
            prefix=source,
            depth=depth + 1,
            limits=limits,
        )
    if lowered.endswith(".rar"):
        return _extract_all_rar_documents(
            payload,
            prefix=source,
            limits=limits,
            depth=depth + 1,
        )
    return None


def _register_extracted_file(
    extracted: list[dict],
    *,
    source: str,
    payload: bytes,
    limits: dict,
) -> None:
    limits["files"] += 1
    limits["bytes"] += len(payload)
    if limits["files"] > MAX_FILES:
        raise ValueError(f"O pacote excede o limite de {MAX_FILES} arquivos.")
    if limits["bytes"] > MAX_UNCOMPRESSED_BYTES:
        raise ValueError("O conteúdo descompactado excede o limite de 300 MB.")
    extracted.append({"source": source, "content": payload})


def _extract_rar_with_rarfile(
    content: bytes,
    *,
    prefix: str,
    limits: dict,
    depth: int,
) -> list[dict]:
    import rarfile

    extracted = []
    with tempfile.NamedTemporaryFile(suffix=".rar", delete=False) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    try:
        with rarfile.RarFile(temp_path) as archive:
            for info in archive.infolist():
                if info.isdir():
                    continue
                payload = archive.read(info)
                source = f"{prefix}/{info.filename}".strip("/")
                nested = _extract_nested_payload(
                    payload=payload,
                    source=source,
                    lowered=info.filename.casefold(),
                    limits=limits,
                    depth=depth,
                )
                if nested is not None:
                    extracted.extend(nested)
                    continue
                _register_extracted_file(
                    extracted,
                    source=source,
                    payload=payload,
                    limits=limits,
                )
    finally:
        Path(temp_path).unlink(missing_ok=True)
    return extracted


def _extract_rar_with_external_tool(
    content: bytes,
    *,
    prefix: str,
    limits: dict,
    depth: int,
) -> list[dict]:
    tool = shutil.which("unar") or shutil.which("bsdtar")
    if not tool:
        raise ValueError(
            "Não foi possível abrir arquivo RAR. O ambiente precisa do unar "
            "ou bsdtar instalado."
        )
    extracted = []
    with tempfile.TemporaryDirectory() as temp_dir:
        rar_path = Path(temp_dir) / "arquivo.rar"
        output_dir = Path(temp_dir) / "saida"
        output_dir.mkdir()
        rar_path.write_bytes(content)
        if Path(tool).name.casefold().startswith("unar"):
            command = [
                tool,
                "-quiet",
                "-force-overwrite",
                "-output-directory",
                str(output_dir),
                str(rar_path),
            ]
        else:
            command = [tool, "-xf", str(rar_path), "-C", str(output_dir)]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if completed.returncode != 0:
            raise ValueError(
                "Não foi possível abrir o RAR. Verifique se o arquivo está íntegro."
            )
        for path in sorted(output_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(output_dir).as_posix()
            payload = path.read_bytes()
            source = f"{prefix}/{relative}".strip("/")
            nested = _extract_nested_payload(
                payload=payload,
                source=source,
                lowered=relative.casefold(),
                limits=limits,
                depth=depth,
            )
            if nested is not None:
                extracted.extend(nested)
                continue
            _register_extracted_file(
                extracted,
                source=source,
                payload=payload,
                limits=limits,
            )
    return extracted


def _extract_package_documents(
    content: bytes,
    package_name: str = "",
    *,
    split_compound_pdfs: bool = True,
    split_only_likely_documents: bool = False,
) -> list[dict]:
    lowered = package_name.casefold()
    limits = {"files": 0, "bytes": 0}
    if lowered.endswith(".rar"):
        try:
            return _expand_compound_pdf_entries(
                _extract_all_rar_documents(
                    content,
                    prefix="",
                    limits=limits,
                    depth=0,
                ),
                enabled=split_compound_pdfs,
                only_likely_documents=split_only_likely_documents,
            )
        except Exception as exc:
            raise ValueError(
                "Não foi possível abrir o RAR. Verifique se o arquivo está íntegro."
            ) from exc
    if lowered.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")):
        try:
            return _expand_compound_pdf_entries(
                _extract_all_tar_documents(
                    content,
                    prefix="",
                    depth=0,
                    limits=limits,
                ),
                enabled=split_compound_pdfs,
                only_likely_documents=split_only_likely_documents,
            )
        except tarfile.ReadError as exc:
            raise ValueError("O arquivo TAR enviado não é válido.") from exc
    return _expand_compound_pdf_entries(
        _extract_all_zip_documents(content),
        enabled=split_compound_pdfs,
        only_likely_documents=split_only_likely_documents,
    )


def _selected_pdf_pages(content: bytes, page_numbers: list[int]) -> bytes:
    reader = PdfReader(BytesIO(content))
    writer = PdfWriter()
    for page_number in page_numbers:
        writer.add_page(reader.pages[page_number - 1])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _pdf_page_count(content: bytes) -> int:
    try:
        return len(PdfReader(BytesIO(content)).pages)
    except Exception:
        return 0


def _should_try_split_pdf(entry: dict, *, only_likely_documents: bool) -> bool:
    normalized_source = normalize_text(entry["source"])
    likely_compound = any(
        marker in normalized_source
        for marker in (
            "doc hab",
            "docs hab",
            "habilitacao",
            "habilitação",
            "registros",
            "documentos",
            "icismep",
            "habilit",
        )
    )
    if likely_compound:
        return True
    if not only_likely_documents:
        return True
    return False


def _expand_compound_pdf_entries(
    entries: list[dict],
    *,
    enabled: bool = True,
    only_likely_documents: bool = False,
) -> list[dict]:
    if not enabled:
        return entries
    expanded = []
    for entry in entries:
        if not entry["source"].casefold().endswith(".pdf"):
            expanded.append(entry)
            continue
        if not _should_try_split_pdf(
            entry,
            only_likely_documents=only_likely_documents,
        ):
            expanded.append(entry)
            continue
        split_entries = _split_compound_pdf_entry(entry)
        expanded.extend(split_entries or [entry])
    return expanded


def _split_compound_pdf_entry(entry: dict) -> list[dict]:
    source = entry["source"]
    normalized_source = normalize_text(source)
    likely_compound = any(
        marker in normalized_source
        for marker in (
            "doc hab",
            "docs hab",
            "habilitacao",
            "habilitação",
            "registros",
            "documentos",
        )
    )
    try:
        with pdfplumber.open(BytesIO(entry["content"])) as pdf:
            if len(pdf.pages) < 4:
                return []
            page_infos = []
            distinct_codes = set()
            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                identification = _identify_document_by_content(text)
                code = identification["code"] if identification else ""
                if code:
                    distinct_codes.add(code)
                page_infos.append((page_number, code, identification))
    except Exception:
        return []

    if len(distinct_codes) < 2 and not likely_compound:
        return []

    groups = []
    current = None
    for page_number, code, identification in page_infos:
        if code:
            if current is None or current["code"] != code:
                current = {
                    "code": code,
                    "label": identification["label"],
                    "pages": [],
                }
                groups.append(current)
        if current is not None:
            current["pages"].append(page_number)

    if len(groups) < 2:
        return []

    parent = str(PurePosixPath(source).parent)
    if parent == ".":
        parent = ""
    stem = PurePosixPath(source).stem
    split_entries = []
    for group in groups:
        pages = sorted(set(group["pages"]))
        if not pages:
            continue
        page_label = (
            str(pages[0])
            if len(pages) == 1
            else f"{pages[0]}-{pages[-1]}"
        )
        split_name = (
            f"{stem} - páginas {page_label} - "
            f"{group['code']} - {group['label']}.pdf"
        )
        split_source = f"{parent}/{split_name}".strip("/")
        try:
            split_content = _selected_pdf_pages(entry["content"], pages)
        except Exception:
            continue
        split_entries.append({"source": split_source, "content": split_content})
    return split_entries


def _safe_basename(name: str) -> str:
    basename = PurePosixPath(name.replace("\\", "/")).name
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", basename).strip(" .")
    return cleaned or "documento_sem_nome"


def _extract_cnpj(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) >= 14:
        return digits[-14:]
    return ""


def _format_cnpj(cnpj: str) -> str:
    digits = _extract_cnpj(cnpj)
    if not digits:
        return ""
    return (
        f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/"
        f"{digits[8:12]}-{digits[12:]}"
    )


def _coerce_date(value: date | str | None) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


def tcu_validation_url(cnpj_or_supplier: str = "") -> str:
    cnpj = _extract_cnpj(cnpj_or_supplier)
    if not cnpj:
        return TCU_CERTIDOES_URL
    return f"{TCU_CERTIDOES_URL}?cpfCnpj={cnpj}"


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


def _supplier_cnpj_from_context(
    *,
    supplier: str,
    source: str,
    default_supplier: str = "",
    winner: dict | None = None,
) -> str:
    if winner:
        cnpj = _extract_cnpj(winner.get("cnpj", ""))
        if cnpj:
            return cnpj
    for value in (supplier, source, default_supplier):
        cnpj = _extract_cnpj(value)
        if cnpj:
            return cnpj
    return ""


def analyze_document_zip(
    content: bytes,
    profile: str,
    technical_qualification: str = "",
    reference_file: tuple[str, bytes] | None = None,
    default_supplier: str = "",
    package_name: str = "",
    *,
    fast_mode: bool = True,
    allow_ocr: bool = False,
    split_compound_pdfs: bool = True,
    read_internal_validity: bool = True,
    session_date: date | str | None = None,
) -> dict:
    if profile not in PROFILE_CHECKLISTS:
        raise ValueError(f"Perfil documental inválido: {profile}")

    entries = _extract_package_documents(
        content,
        package_name,
        split_compound_pdfs=split_compound_pdfs,
        split_only_likely_documents=fast_mode,
    )
    winners = _parse_winners_report(reference_file)
    session_reference_date = _coerce_date(session_date)
    required_technical = set(
        _required_technical_documents(technical_qualification)
    )
    documents = []
    for entry in entries:
        filename = _safe_basename(entry["source"])
        suffix = PurePosixPath(filename).suffix.casefold()
        preliminary_identification = (
            _identification_from_split_filename(filename)
            or identify_document(entry["source"], "")
            or identify_document(filename, "")
        )
        can_skip_content = fast_mode and not allow_ocr and (
            preliminary_identification is not None
            or suffix in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
        )
        if can_skip_content:
            searchable_text, ocr_used = "", False
            identification = preliminary_identification
        else:
            searchable_text, ocr_used = _extract_searchable_text(
                filename,
                entry["content"],
                allow_ocr=allow_ocr,
            )
            identification = preliminary_identification or identify_document(
                filename,
                searchable_text,
            )
        validity = _detect_validity(
            filename,
            searchable_text,
            reference_date=session_reference_date,
        )
        if (
            not identification
            or identification["code"] not in INTERNAL_VALIDITY_CODES
        ):
            validity = {
                "validity_date": "",
                "validity_status": "Não se aplica",
            }
        requirement = (
            (identification["code"], identification["label"])
            if identification
            else ("", "")
        )
        is_potentially_required = bool(
            identification
            and (
                identification["code"] in STANDARD_REQUIRED_CODES
                or identification["code"] in CONDITIONAL_DOCUMENT_CODES
                or requirement in required_technical
            )
        )
        if (
            can_skip_content
            and is_potentially_required
            and not validity["validity_date"]
            and suffix == ".pdf"
            and read_internal_validity
            and identification
            and identification["code"] in INTERNAL_VALIDITY_CODES
            and "sem val" not in normalize_text(filename)
            and "s val" not in normalize_text(filename)
        ):
            searchable_text, ocr_used = _extract_searchable_text(
                filename,
                entry["content"],
                allow_ocr=False,
            )
            validity = _detect_validity(
                filename,
                searchable_text,
                reference_date=session_reference_date,
            )
        supplier = _supplier_from_source(
            entry["source"],
            winners,
            default_supplier,
        )
        winner = _winner_for_supplier(supplier, winners)
        supplier_cnpj = _supplier_cnpj_from_context(
            supplier=supplier,
            source=entry["source"],
            default_supplier=default_supplier,
            winner=winner,
        )
        validation_url, validation_note, validation_data = document_validation(
            identification["code"] if identification else "",
            searchable_text,
            supplier_cnpj=supplier_cnpj,
            validity_date=validity["validity_date"],
        )
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
                "supplier_cnpj": supplier_cnpj,
                "name": filename,
                "standardized_name": standardized_name,
                "identified": identification is not None,
                "document_code": identification["code"] if identification else "",
                "document_label": identification["label"] if identification else "",
                "document_group": document_group(
                    identification["code"] if identification else ""
                ),
                "validation_url": validation_url,
                "validation_note": validation_note,
                "validation_data": validation_data,
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

    checklist = _build_checklist(profile, documents)

    totals = {
        category: sum(document["category"] == category for document in documents)
        for category in ("BÁSICOS", "TÉCNICOS", "NÃO CLASSIFICADOS")
    }
    suppliers = sorted({document["supplier"] for document in documents})
    supplier_cnpjs = {}
    for supplier in suppliers:
        cnpj = next(
            (
                document["supplier_cnpj"]
                for document in documents
                if document["supplier"] == supplier and document["supplier_cnpj"]
            ),
            "",
        )
        supplier_cnpjs[supplier] = cnpj
    return {
        "profile": profile,
        "technical_qualification": technical_qualification.strip(),
        "documents": documents,
        "suppliers": suppliers,
        "supplier_cnpjs": supplier_cnpjs,
        "winners_identified": len(winners),
        "checklist": checklist,
        "totals": totals,
        "ocr_candidates": sum(document["ocr_candidate"] for document in documents),
        "ocr_processed": sum(document["ocr_used"] for document in documents),
        "package_name": package_name,
        "fast_mode": fast_mode,
        "allow_ocr": allow_ocr,
        "split_compound_pdfs": split_compound_pdfs,
        "read_internal_validity": read_internal_validity,
        "_entry_contents": {
            entry["source"]: entry["content"] for entry in entries
        },
        "session_date": (
            session_reference_date.strftime("%d/%m/%Y")
            if session_reference_date
            else ""
        ),
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
    extracted_entries = _entries_from_analysis_or_package(content, analysis)

    with ZipFile(output_buffer, "w", ZIP_DEFLATED) as target:
        output_names: dict[str, int] = {}
        catalog_groups: dict[str, list[tuple[bytes, dict, list[int]]]] = {}
        suppliers = analysis.get("suppliers", []) or ["Fornecedor não identificado"]
        if reference_file:
            reference_name, reference_content = reference_file
            for supplier in suppliers:
                target.writestr(
                    (
                        f"{supplier}/01 - Documento do Processo/"
                        f"01 - {_safe_basename(reference_name)}"
                    ),
                    reference_content,
                )
        for supplier in suppliers:
            supplier_cnpj = analysis.get("supplier_cnpjs", {}).get(supplier, "")
            formatted_cnpj = _format_cnpj(supplier_cnpj) or "não identificado"
            tcu_url = tcu_validation_url(supplier_cnpj or supplier)
            target.writestr(
                (
                    f"{supplier}/02 - Consulta TCU e CEIS-CNEP/"
                    "02 - Roteiro de consulta.txt"
                ),
                "\n".join(
                    [
                        "10.5 - Consulta Consolidada TCU / CEIS-CNEP",
                        f"CNPJ do fornecedor: {formatted_cnpj}",
                        "",
                        "1) Consultar TCU/APF:",
                        tcu_url,
                        "",
                        "2) Se necessário, conferir CEIS/CNEP no Portal da Transparência:",
                        "https://portaldatransparencia.gov.br/sancoes/consulta",
                    ]
                ).encode("utf-8"),
            )

        sorted_entries = [
            entry for entry in extracted_entries if entry["source"] in document_map
        ]
        sorted_entries.sort(
            key=lambda entry: (
                document_map[entry["source"]]["supplier"],
                _document_order(document_map[entry["source"]]["document_code"]),
                document_map[entry["source"]]["standardized_name"],
            )
        )

        for entry in sorted_entries:
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
                catalog_groups.setdefault(document["supplier"], []).append(
                    (payload, document, selected_pages)
                )
                continue

            if document["selected_for_requirement"]:
                folder = _organized_folder(document)
                desired_name = document["standardized_name"]
            elif document["identified"]:
                folder = (
                    f"{document['supplier']}/06 - Documentos Fora da Lista"
                )
                desired_name = document["name"]
            else:
                folder = (
                    f"{document['supplier']}/07 - Documentos Não Identificados"
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

        for supplier, catalog_items in catalog_groups.items():
            target.writestr(
                (
                    f"{supplier}/05 - Proposta e Itens Vencedores/"
                    "7.0.4 - Catálogo Itens Vencedores.pdf"
                ),
                _merge_pdf_documents([item[0] for item in catalog_items]),
            )
            catalog_lines = ["PÁGINAS LOCALIZADAS NO CATÁLOGO", ""]
            for _, document, pages in catalog_items:
                if pages:
                    catalog_lines.append(
                        f"- {document['name']}: páginas originais "
                        f"{', '.join(str(page) for page in pages)}."
                    )
                else:
                    catalog_lines.append(
                        f"- {document['name']}: não foi possível localizar "
                        "as páginas dos itens vencedores com segurança; "
                        "o catálogo foi mantido para conferência manual."
                    )
            target.writestr(
                (
                    f"{supplier}/05 - Proposta e Itens Vencedores/"
                    "PÁGINAS DO CATÁLOGO.txt"
                ),
                "\n".join(catalog_lines).encode("utf-8"),
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
                "site_validacao",
                "dados_validacao",
                "orientacao_validacao",
                "paginas_catalogo",
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
                    document["validation_url"],
                    document.get("validation_data", ""),
                    document["validation_note"],
                    ", ".join(
                        str(page)
                        for page in document.get("catalog_pages_selected", [])
                    ),
                ]
            )
        target.writestr(
            "RELATORIO_INTELIGENCIA_DOCUMENTAL.csv",
            report.getvalue().encode("utf-8-sig"),
        )

        checklist_lines = [
            f"Perfil documental: {analysis['profile']}",
            (
                f"Data da sessão usada para validade: {analysis['session_date']}"
                if analysis.get("session_date")
                else "Data da sessão usada para validade: data atual do processamento"
            ),
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
            supplier_documents_sorted = sorted(
                supplier_documents,
                key=lambda document: (
                    _document_order(document["document_code"]),
                    document["standardized_name"],
                ),
            )
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
            validation_documents = [
                document
                for document in supplier_documents_sorted
                if document["selected_for_requirement"]
                and document["document_code"]
                in {
                    "7.0.1",
                    "10.7.1",
                    "10.7.2",
                    "10.7.3",
                    "10.7.4",
                    "10.7.5",
                    "10.7.6",
                    "10.8.1",
                }
            ]
            catalog_documents = [
                document
                for document in supplier_documents_sorted
                if document["selected_for_requirement"]
                and document["document_code"] == "7.0.4"
            ]
            supplier_cnpj = analysis.get("supplier_cnpjs", {}).get(supplier, "")
            formatted_cnpj = _format_cnpj(supplier_cnpj) or "não identificado"
            tcu_url = tcu_validation_url(supplier_cnpj or supplier)
            supplier_lines = [
                f"Fornecedor: {supplier}",
                f"CNPJ: {formatted_cnpj}",
                f"Perfil documental: {analysis['profile']}",
                (
                    f"Data da sessão usada para validade: {analysis['session_date']}"
                    if analysis.get("session_date")
                    else "Data da sessão usada para validade: data atual do processamento"
                ),
                "",
                "ORDEM DA PASTA:",
                "01 - Documento do Processo",
                "02 - Consulta TCU e CEIS-CNEP",
                "03 - Documentos de Habilitação",
                "04 - Qualificação Técnica",
                "05 - Proposta e Itens Vencedores",
                "",
                "QUALIFICAÇÃO TÉCNICA EXIGIDA (OPCIONAL):",
                analysis.get("technical_qualification") or "Não informada.",
                "",
                "DOCUMENTOS LOCALIZADOS:",
                *[
                    f"[OK] {document['document_code']} - {document['document_label']}"
                    for document in supplier_documents_sorted
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
                "",
                "ROTEIRO DE VALIDAÇÃO:",
                "- 10.5 - Consulta Consolidada TCU / CEIS-CNEP | "
                f"CNPJ: {formatted_cnpj} | Situação: A conferir | "
                f"Conferência: {tcu_url}",
                *(
                    [
                        f"- {document['standardized_name']} | "
                        f"Validade: "
                        f"{document['validity_date'] or 'não identificada'} | "
                        f"Situação: {document['validity_status']} | "
                        f"Conferência: "
                        f"{document['validation_url'] or document['validation_note']}"
                        for document in validation_documents
                    ]
                    or ["Nenhum documento de validação localizado."]
                ),
                "",
                "CATÁLOGO E ITENS VENCEDORES:",
                *(
                    [
                        (
                            f"- {document['standardized_name']}: páginas originais "
                            f"{', '.join(str(page) for page in document.get('catalog_pages_selected', []))}"
                        )
                        if document.get("catalog_pages_selected")
                        else (
                            f"- {document['standardized_name']}: páginas dos itens "
                            "vencedores não localizadas automaticamente; conferir manualmente."
                        )
                        for document in catalog_documents
                    ]
                    or ["Nenhum catálogo selecionado para os itens vencedores."]
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
