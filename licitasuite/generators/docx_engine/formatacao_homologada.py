from __future__ import annotations

from pathlib import Path
from typing import Any
import re
from zipfile import ZipFile, ZIP_DEFLATED

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _formatar_milhar(valor: Any) -> str:
    texto = _texto(valor)
    if not texto:
        return ""

    texto_limpo = texto.replace(".", "").replace(",", "").strip()

    if not re.fullmatch(r"\d+", texto_limpo):
        return texto

    try:
        return f"{int(texto_limpo):,}".replace(",", ".")
    except Exception:
        return texto


def _title_empresa(nome: str) -> str:
    especiais = {"LTDA", "S.A.", "SA", "ME", "EPP", "EIRELI"}
    partes = _texto(nome).lower().split()
    saida = []

    for parte in partes:
        p = parte.upper().replace("S/A", "S.A.")
        if p in especiais:
            saida.append(p)
        else:
            saida.append(parte.capitalize())

    return " ".join(saida)


def _cell_text(cell) -> str:
    return " ".join(p.text for p in cell.paragraphs).strip()


def _limpar_paragrafo(paragraph):
    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)


def _run(paragraph, text: str, bold: bool = False, size: int = 11):
    r = paragraph.add_run(text)
    r.bold = bool(bold)
    r.font.name = "Arial"
    r.font.size = Pt(size)
    return r


def _set_run(run, bold: bool = False, size: int = 11):
    run.bold = bool(bold)
    run.font.name = "Arial"
    run.font.size = Pt(size)


def _set_cell_text(cell, text: str, size: int = 8, bold: bool = False, center: bool = True):
    cell.text = ""
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = cell.paragraphs[0]
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    _set_run(r, bold=bold, size=size)


def _safe_get(obj: Any, *names: str, default: str = "") -> str:
    for name in names:
        value = getattr(obj, name, None)
        if value:
            return _texto(value)
    return default


def _get_from_supplier(ata: Any, *names: str, default: str = "") -> str:
    for source_name in ("fornecedor", "supplier", "dados_fornecedor", "fornecedor_dados"):
        source = getattr(ata, source_name, None)
        if source:
            for name in names:
                value = getattr(source, name, None)
                if value:
                    return _texto(value)
    return default


def _ata_empresa(ata: Any) -> str:
    return (
        _safe_get(ata, "fornecedor_nome", "razao_social", "nome_fornecedor")
        or _get_from_supplier(ata, "razao_social", "nome", "fornecedor_nome")
    )


def _ata_endereco(ata: Any) -> str:
    return _safe_get(ata, "endereco_fornecedor", "endereco") or _get_from_supplier(ata, "endereco")


def _ata_cep(ata: Any) -> str:
    return _safe_get(ata, "cep") or _get_from_supplier(ata, "cep")


def _ata_fone(ata: Any) -> str:
    return _safe_get(ata, "telefone", "fone") or _get_from_supplier(ata, "telefone", "fone")


def _ata_email(ata: Any) -> str:
    return _safe_get(ata, "email", "e_mail") or _get_from_supplier(ata, "email", "e_mail")


def _ata_cnpj(ata: Any) -> str:
    return _safe_get(ata, "cnpj") or _get_from_supplier(ata, "cnpj")


def _ata_ie(ata: Any) -> str:
    return _safe_get(ata, "inscricao_estadual", "ie") or _get_from_supplier(ata, "inscricao_estadual", "ie")


def _ata_representante(ata: Any) -> str:
    return (
        _safe_get(ata, "representante", "representante_legal", "socio")
        or _get_from_supplier(ata, "representante", "representante_legal", "socio")
    )


def _ata_cpf(ata: Any) -> str:
    return _safe_get(ata, "cpf") or _get_from_supplier(ata, "cpf")


def _ata_rg(ata: Any) -> str:
    return _safe_get(ata, "rg") or _get_from_supplier(ata, "rg")


def _ata_orgao(ata: Any) -> str:
    return _safe_get(ata, "orgao", "orgao_expedidor") or _get_from_supplier(ata, "orgao", "orgao_expedidor")


def _extrair_processo_pregao(texto: str) -> tuple[str, str]:
    processo = ""
    pregao = ""

    m = re.search(r"PROCESSO\s+LICITAT[ÓO]RIO\s+N[º°]\s*([\d./-]+)", texto, flags=re.I)
    if m:
        processo = m.group(1)

    m = re.search(r"PREG[ÃA]O\s+ELETR[ÔO]NICO\s+N[º°]\s*([\d./-]+)", texto, flags=re.I)
    if m:
        pregao = m.group(1)

    return processo, pregao


def _normalizar_representante_assinatura(representante: str) -> str:
    rep = _texto(representante)
    rep = re.sub(r"^(seu|sua)\s+s[oó]cio\s+Sr\.?\s+", "", rep, flags=re.I).strip()
    rep = re.sub(r"^(Sr\.?|Sra\.?)\s+", "", rep, flags=re.I).strip()
    return rep or representante


def formatar_preambulo(document: Document, ata: Any):
    empresa = _ata_empresa(ata).upper()
    if not empresa:
        return

    for p in document.paragraphs:
        txt = p.text or ""
        txt_norm = txt.upper()

        if "NESTE ATO REPRESENTADO POR SEU DIRETOR INSTITUCIONAL" not in txt_norm:
            continue

        if "PROCESSO LICITATÓRIO" not in txt_norm and "PROCESSO LICITATORIO" not in txt_norm:
            continue

        processo, pregao = _extrair_processo_pregao(txt)

        endereco = _ata_endereco(ata)
        cep = _ata_cep(ata)
        fone = _ata_fone(ata)
        email = _ata_email(ata)
        cnpj = _ata_cnpj(ata)
        ie = _ata_ie(ata)
        representante = _ata_representante(ata)
        cpf = _ata_cpf(ata)
        rg = _ata_rg(ata)
        orgao = _ata_orgao(ata)

        _limpar_paragrafo(p)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        _run(p, "O ", False)
        _run(p, "CONSÓRCIO PÚBLICO INSTITUIÇÃO DE COOPERAÇÃO INTERMUNICIPAL DO MÉDIO PARAOPEBA - ICISMEP, CNPJ Nº 05.802.877/0001-10", True)
        _run(p, ", órgão gerenciador, com sede na Rua Marciano Henriques, n° 107, Bairro Centro, no Município de Igarapé, Estado de Minas Gerais, CEP 32.510-008, a seguir denominado Consórcio ICISMEP, neste ato representado por seu diretor institucional Sr. ", False)
        _run(p, "Eustáquio da Abadia Amaral", False)
        _run(p, " e ", False)
        _run(p, empresa, True)
        _run(p, f", com sede na {endereco}, CEP {cep}, Fone {fone}, e-mail {email}, inscrita no CNPJ sob o n.º {cnpj}", False)

        if ie:
            _run(p, f", Inscrição Estadual n.º {ie}", False)

        _run(p, ", neste ato representada por ", False)
        _run(p, representante, True)
        _run(p, f", inscrito no CPF sob o nº {cpf} e portador da Carteira de Identidade n° {rg}, expedida pela {orgao}, nos termos do artigo 40, II da Lei Federal n° 14.133/21, observadas, ainda, as disposições do Edital do ", False)
        _run(p, f"PROCESSO LICITATÓRIO Nº {processo}", True)
        _run(p, ", na modalidade ", False)
        _run(p, f"PREGÃO ELETRÔNICO Nº {pregao}", True)
        _run(p, ", do tipo menor preço, auxiliado pelo Sistema de Registro de Preços, regido pela Lei Federal n° 14.133/21, e regulamentado pelo Decreto Federal n° 11.462/23, e demais disposições legais aplicáveis, de acordo com o resultado da classificação das propostas apresentadas no Pregão, resolvem registrar os preços da empresa acima citada, de acordo com o item disputado e a classificação por ela alcançada, observadas as condições do Edital que integram este instrumento de registro, mediante as condições a seguir situadas:", False)
        return


def formatar_quantidade_clausula_4(document: Document):
    for table in document.tables:
        quant_idx = None

        for row in table.rows[:3]:
            headers = [_cell_text(c).upper().replace(".", "").strip() for c in row.cells]
            if "QUANT" in headers:
                quant_idx = headers.index("QUANT")
                break

        if quant_idx is None:
            continue

        for row in table.rows[1:]:
            if quant_idx >= len(row.cells):
                continue

            cell = row.cells[quant_idx]
            txt = _cell_text(cell)
            novo = _formatar_milhar(txt)

            if novo != txt or txt:
                _set_cell_text(cell, novo, size=8, bold=False, center=True)


def formatar_assinaturas(document: Document, ata: Any):
    empresa = _ata_empresa(ata)
    representante = _ata_representante(ata)

    if not empresa or not representante:
        return

    empresa_ass = _title_empresa(empresa)
    representante_ass = _normalizar_representante_assinatura(representante)

    # Ajusta apenas o bloco do fornecedor se for localizado. Não mexe no bloco do diretor.
    for p in document.paragraphs:
        txt = (p.text or "").strip()
        low = txt.lower()

        # Remove blocos antigos pequenos criados acima da assinatura.
        if (empresa.lower() in low or representante.lower() in low) and len(txt) <= 180:
            _limpar_paragrafo(p)

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                text = _cell_text(cell)
                low = text.lower()

                if empresa.lower() in low or representante.lower() in low:
                    cell.text = ""
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

                    # quatro linhas de espaçamento acima do bloco do fornecedor
                    _run(p, "\n\n\n\n", False)
                    _run(p, representante_ass, True)
                    _run(p, "\n", False)
                    _run(p, empresa_ass, True)


def aplicar_formatacao_homologada(docx_path: str | Path, ata: Any):
    docx_path = Path(docx_path)
    document = Document(docx_path)

    formatar_preambulo(document, ata)
    formatar_quantidade_clausula_4(document)
    formatar_assinaturas(document, ata)

    document.save(docx_path)


def aplicar_em_lote(files: list, atas: list):
    for idx, file in enumerate(files):
        ata = atas[idx] if idx < len(atas) else None
        if not ata:
            continue
        aplicar_formatacao_homologada(file, ata)


def recriar_zip(files: list, zip_path: str | Path):
    zip_path = Path(zip_path)
    if not files or not zip_path:
        return zip_path

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as z:
        for f in files:
            p = Path(f)
            if p.exists():
                z.write(p, p.name)

    return zip_path
