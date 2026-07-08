from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import re
import xml.etree.ElementTree as ET
from typing import Any

import pdfplumber


SUPPLIER_HEADER_RE = re.compile(r"(?m)^(.+?)\s+\|\s*Tipo:", flags=re.I)
TOTAL_VENCEDOR_RE = re.compile(
    r"TOTAL\s+DO\s+VENCEDOR\s+R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})",
    flags=re.I,
)
ITEM_START_RE = re.compile(r"(?m)^(\d{4})\s+")
MONEY_RE = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})")
ANY_MONEY_RE = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})(?!\d)")


def _money(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("R$", "").strip()
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        return 0.0


def _fmt_money(value: Any) -> str:
    value = _money(value)
    return "R$ " + f"{value:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _norm(value: Any) -> str:
    text = str(value or "").upper()
    repl = {
        "Á": "A", "À": "A", "Â": "A", "Ã": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Ô": "O", "Õ": "O",
        "Ú": "U",
        "Ç": "C",
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _supplier_key(name: Any) -> str:
    text = _norm(name)
    stopwords = {
        "LTDA", "EIRELI", "SA", "S", "A", "ME", "EPP", "SS",
        "COMERCIO", "COMERCIAL", "DISTRIBUIDORA", "DISTRIBUICAO",
        "MEDICAMENTOS", "PRODUTOS", "PRODUTO", "HOSPITALARES",
        "IMPORTACAO", "EXPORTACAO", "SERVICOS", "FARMACEUTICA",
        "FARMACEUTICOS",
    }
    tokens = [t for t in text.split() if t not in stopwords]
    return " ".join(tokens[:5])


def _short_key(name: Any) -> str:
    return " ".join(_supplier_key(name).split()[:2])


def _prepare_text(text: str) -> str:
    text = text or ""
    text = text.replace("\xa0", " ")
    text = text.replace("\u00ad", "")
    text = text.replace("\ufffe", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _read_pdf_text(pdf_path: Path) -> str:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text(layout=True, x_tolerance=1, y_tolerance=3) or "")
    return "\n".join(pages)


def _find_pdf_in_zip_or_folder(path: Path | None) -> Path | None:
    if not path:
        return None

    if path.is_file() and path.suffix.lower() == ".pdf":
        return path

    if path.is_dir():
        pdfs = list(path.rglob("*.pdf"))
        if not pdfs:
            return None
        pdfs.sort(key=lambda p: (0 if "venced" in p.name.lower() else 1, len(p.name)))
        return pdfs[0]

    if path.is_file() and path.suffix.lower() == ".zip":
        temp = Path("temp/conferencia_pdf")
        temp.mkdir(parents=True, exist_ok=True)

        with ZipFile(path, "r") as z:
            pdfs = [n for n in z.namelist() if n.lower().endswith(".pdf")]
            if not pdfs:
                return None
            pdfs.sort(key=lambda n: (0 if "venced" in n.lower() else 1, len(n)))
            out = temp / Path(pdfs[0]).name
            out.write_bytes(z.read(pdfs[0]))
            return out

    return None


def _split_supplier_blocks(text: str) -> list[str]:
    headers = list(SUPPLIER_HEADER_RE.finditer(text))
    blocks = []
    for i, h in enumerate(headers):
        start = h.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append(block)
    return blocks


def _parse_pdf_financeiro(pdf_path: Path) -> list[dict[str, Any]]:
    text = _prepare_text(_read_pdf_text(pdf_path))
    rows = []

    for block in _split_supplier_blocks(text):
        name_match = re.search(r"^(.+?)\s+\|\s*Tipo:", block, flags=re.I | re.M)
        if not name_match:
            continue

        nome = re.sub(r"\s+", " ", name_match.group(1)).strip(" -|")
        total_match = TOTAL_VENCEDOR_RE.search(block)
        total_oficial = _money(total_match.group("total")) if total_match else 0.0

        # Região entre cabeçalho da tabela e TOTAL DO VENCEDOR.
        header = re.search(
            r"C[oó]digo\s+Produto\s+Modelo\s+Marca/Fabricante\s+Qtde\s+Valor\s+Unit[aá]rio\s+Valor\s+Total",
            block,
            flags=re.I,
        )

        table = ""
        if header:
            start = header.end()
            total_pos = re.search(r"TOTAL\s+DO\s+VENCEDOR", block[start:], flags=re.I)
            end = start + total_pos.start() if total_pos else len(block)
            table = block[start:end]

        item_values = []
        item_codes = []

        if table:
            starts = list(ITEM_START_RE.finditer(table))
            for i, s in enumerate(starts):
                item_code = s.group(1)
                item_codes.append(item_code)
                start = s.start()
                end = starts[i + 1].start() if i + 1 < len(starts) else len(table)
                row = re.sub(r"\s+", " ", table[start:end]).strip()

                # Busca valores com R$; o total é geralmente o segundo/último valor.
                vals = MONEY_RE.findall(row)
                if len(vals) >= 2:
                    item_values.append(_money(vals[-1]))
                elif vals:
                    # Se só tem um valor com R$, busca número monetário solto depois dele.
                    after = row[row.find(vals[-1]) + len(vals[-1]):]
                    loose = ANY_MONEY_RE.findall(after)
                    loose = [x for x in loose if x != vals[-1]]
                    if loose:
                        item_values.append(_money(loose[-1]))
                    else:
                        item_values.append(0.0)
                else:
                    nums = ANY_MONEY_RE.findall(row)
                    item_values.append(_money(nums[-1]) if nums else 0.0)

        soma_itens_pdf = sum(item_values)

        if len(item_values) == 1 and total_oficial:
            # Item único: o total oficial deve coincidir com o único item.
            soma_itens_pdf = item_values[0]

        status_soma = "OK"
        if total_oficial and abs(soma_itens_pdf - total_oficial) > 0.05:
            status_soma = "DIVERGENTE - CORRIGIR MANUALMENTE"

        rows.append({
            "nome": nome,
            "key": _supplier_key(nome),
            "short_key": _short_key(nome),
            "itens_pdf": item_codes,
            "total_oficial_vencedor": total_oficial,
            "soma_itens_pdf": soma_itens_pdf,
            "status_soma_pdf": status_soma,
        })

    return rows


def _docx_text(path: Path) -> str:
    try:
        with ZipFile(path, "r") as z:
            xml_names = [n for n in z.namelist() if n.startswith("word/") and n.endswith(".xml")]
            parts = []
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for name in xml_names:
                if not (name.endswith("document.xml") or "header" in name or "footer" in name):
                    continue
                root = ET.fromstring(z.read(name))
                for node in root.findall(".//w:t", ns):
                    if node.text:
                        parts.append(node.text)
            return " ".join(parts)
    except Exception:
        return ""


def _docx_rows(docx_files: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for file in docx_files:
        stem = file.stem
        nome = stem.split(" - ", 1)[1] if " - " in stem else stem
        text = _docx_text(file)
        money_values = [_money(v) for v in MONEY_RE.findall(text)]
        rows.append({
            "arquivo": file.name,
            "nome": nome,
            "key": _supplier_key(nome),
            "short_key": _short_key(nome),
            "text": text,
            "money_values": money_values,
        })
    return rows


def _match_rows(pdf_rows: list[dict[str, Any]], docx_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}

    for pdf in pdf_rows:
        key = pdf.get("key", "")
        short = pdf.get("short_key", "")
        found = None

        for docx in docx_rows:
            dk = docx.get("key", "")
            ds = docx.get("short_key", "")
            if key and dk and (key == dk or key in dk or dk in key):
                found = docx
                break
            if short and ds and short == ds:
                found = docx
                break
            if short and dk and short in dk:
                found = docx
                break

        if found:
            result[key] = found

    return result


def build_conferencia(zip_path: Path | None, output_dir: Path, docx_files: list[Path]) -> dict[str, Any]:
    pdf_path = _find_pdf_in_zip_or_folder(zip_path)
    pdf_rows = _parse_pdf_financeiro(pdf_path) if pdf_path else []
    docx_rows = _docx_rows(docx_files)

    matched = _match_rows(pdf_rows, docx_rows)

    linhas_financeiras = []
    faltando_docx = []

    for pdf in pdf_rows:
        key = pdf["key"]
        docx = matched.get(key)

        total_oficial = pdf["total_oficial_vencedor"]
        soma_itens_pdf = pdf["soma_itens_pdf"]

        status_docx = "DOCX NÃO LOCALIZADO"
        valor_encontrado_na_ata = ""
        observacao = ""

        if not docx:
            faltando_docx.append(pdf["nome"])
        else:
            # Não tenta inventar o valor da ata.
            # Apenas verifica se o TOTAL DO VENCEDOR aparece no DOCX.
            values = docx.get("money_values", [])
            exists = any(abs(v - total_oficial) <= 0.05 for v in values)
            if exists:
                status_docx = "OK"
                valor_encontrado_na_ata = _fmt_money(total_oficial)
            else:
                status_docx = "DIVERGENTE - TOTAL DO VENCEDOR NÃO ENCONTRADO NA ATA"
                valor_encontrado_na_ata = "NÃO LOCALIZADO"
                observacao = "Conferir manualmente a ata. O valor oficial do vencedor não foi localizado no DOCX."

        status_soma = pdf["status_soma_pdf"]
        if status_soma != "OK":
            observacao = (
                observacao + " | " if observacao else ""
            ) + "Soma dos itens extraídos do PDF não fecha com TOTAL DO VENCEDOR. Corrigir manualmente."

        linhas_financeiras.append({
            "fornecedor": pdf["nome"],
            "itens_pdf": ", ".join(pdf.get("itens_pdf", [])),
            "total_vencedor_pdf": total_oficial,
            "soma_itens_pdf": soma_itens_pdf,
            "status_soma_pdf": status_soma,
            "valor_na_ata": valor_encontrado_na_ata,
            "status_ata": status_docx,
            "observacao": observacao,
        })

    divergencias = [
        x for x in linhas_financeiras
        if x["status_soma_pdf"] != "OK" or x["status_ata"] != "OK"
    ]

    return {
        "pdf_path": str(pdf_path) if pdf_path else "",
        "total_fornecedores_pdf": len(pdf_rows),
        "total_docx": len(docx_files),
        "valor_total_pdf_oficial": sum(x["total_oficial_vencedor"] for x in pdf_rows),
        "soma_itens_pdf": sum(x["soma_itens_pdf"] for x in pdf_rows),
        "faltando_docx": faltando_docx,
        "linhas_financeiras": linhas_financeiras,
        "divergencias_financeiras": divergencias,
        "ok": not faltando_docx and not divergencias,
    }


def write_conferencia_xlsx(conferencia: dict[str, Any], output_dir: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "RELATORIO_CONFERENCIA_AUTOMATICA.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo"

    rows = [
        ["Conferência financeira oficial", ""],
        ["PDF usado", conferencia.get("pdf_path", "")],
        ["Fornecedores no PDF", conferencia.get("total_fornecedores_pdf", 0)],
        ["Arquivos DOCX gerados", conferencia.get("total_docx", 0)],
        ["Valor total oficial PDF", _fmt_money(conferencia.get("valor_total_pdf_oficial", 0))],
        ["Soma dos itens lidos no PDF", _fmt_money(conferencia.get("soma_itens_pdf", 0))],
        ["Status", "OK" if conferencia.get("ok") else "VERIFICAR PENDÊNCIAS"],
    ]

    for row in rows:
        ws.append(row)

    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 100

    red_fill = PatternFill("solid", fgColor="F8D7DA")
    green_fill = PatternFill("solid", fgColor="D9EAD3")
    yellow_fill = PatternFill("solid", fgColor="FFF3CD")
    blue_fill = PatternFill("solid", fgColor="073F9E")
    white_font = Font(color="FFFFFF", bold=True)
    bold = Font(bold=True)
    thin = Side(style="thin", color="D9E2F3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"].font = Font(bold=True, size=15, color="073F9E")
    ws["B7"].fill = green_fill if conferencia.get("ok") else red_fill

    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = border

    sh = wb.create_sheet("Conferência Financeira")
    headers = [
        "FORNECEDOR",
        "ITENS PDF",
        "TOTAL DO VENCEDOR PDF",
        "SOMA DOS ITENS PDF",
        "STATUS SOMA PDF",
        "VALOR LOCALIZADO NA ATA",
        "STATUS ATA",
        "OBSERVAÇÃO / CORREÇÃO MANUAL",
    ]
    sh.append(headers)

    for cell in sh[1]:
        cell.font = white_font
        cell.fill = blue_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    for row in conferencia.get("linhas_financeiras", []):
        sh.append([
            row["fornecedor"],
            row["itens_pdf"],
            _fmt_money(row["total_vencedor_pdf"]),
            _fmt_money(row["soma_itens_pdf"]),
            row["status_soma_pdf"],
            row["valor_na_ata"],
            row["status_ata"],
            row["observacao"],
        ])

    for row in sh.iter_rows(min_row=2):
        status_soma = row[4].value
        status_ata = row[6].value

        fill = None
        if status_soma != "OK" or status_ata != "OK":
            fill = red_fill

        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = border
            if fill:
                cell.fill = fill

    widths = [42, 28, 24, 24, 28, 26, 40, 65]
    for idx, width in enumerate(widths, start=1):
        sh.column_dimensions[chr(64 + idx)].width = width

    sh.freeze_panes = "A2"
    sh.auto_filter.ref = sh.dimensions

    wb.save(out)
    return out


def add_conferencia_to_zip(zip_path: Path, conferencia_file: Path) -> Path:
    if not conferencia_file or not conferencia_file.exists():
        return zip_path

    tmp = zip_path.with_suffix(".tmp.zip")

    with ZipFile(zip_path, "r") as zin:
        existing = {item.filename for item in zin.infolist()}

        with ZipFile(tmp, "w", ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))

            if conferencia_file.name not in existing:
                zout.write(conferencia_file, conferencia_file.name)

    tmp.replace(zip_path)
    return zip_path


def format_conferencia_markdown(conferencia: dict[str, Any]) -> str:
    if conferencia.get("ok"):
        return (
            "✅ Conferência financeira oficial OK\n\n"
            f"- Fornecedores no PDF: **{conferencia.get('total_fornecedores_pdf', 0)}**\n"
            f"- DOCX gerados: **{conferencia.get('total_docx', 0)}**\n"
            f"- Valor total oficial PDF: **{_fmt_money(conferencia.get('valor_total_pdf_oficial', 0))}**\n"
            f"- Soma dos itens PDF: **{_fmt_money(conferencia.get('soma_itens_pdf', 0))}**"
        )

    parts = [
        "⚠️ Conferência financeira oficial encontrou pendências",
        "",
        f"- Fornecedores no PDF: **{conferencia.get('total_fornecedores_pdf', 0)}**",
        f"- DOCX gerados: **{conferencia.get('total_docx', 0)}**",
        f"- Valor total oficial PDF: **{_fmt_money(conferencia.get('valor_total_pdf_oficial', 0))}**",
        f"- Soma dos itens PDF: **{_fmt_money(conferencia.get('soma_itens_pdf', 0))}**",
        "",
        "**Pendências principais:**",
    ]

    for row in conferencia.get("divergencias_financeiras", [])[:12]:
        parts.append(
            f"- {row['fornecedor']}: {row['status_soma_pdf']} | {row['status_ata']}"
        )

    return "\n".join(parts)
