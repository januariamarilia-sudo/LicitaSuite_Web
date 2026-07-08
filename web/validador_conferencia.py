from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import re
from typing import Any


def _money(value: Any) -> float:
    if value is None:
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    text = text.replace("R$", "").strip()
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
        "COMERCIO", "DISTRIBUIDORA", "DISTRIBUICAO",
        "MEDICAMENTOS", "PRODUTOS", "PRODUTO", "HOSPITALARES",
        "IMPORTACAO", "EXPORTACAO", "SERVICOS", "FARMACEUTICA",
        "FARMACEUTICOS", "FARMACEUTICA", "COMERCIAL",
    }

    tokens = [t for t in text.split() if t not in stopwords]

    # Usa tokens fortes, mas mantém tamanho suficiente para diferenciar fornecedores.
    return " ".join(tokens[:5])


def _short_key(name: Any) -> str:
    tokens = _supplier_key(name).split()
    return " ".join(tokens[:2])


def _read_relatorio_json(output_dir: Path) -> dict[str, Any] | None:
    candidates = [
        output_dir / "relatorio_conferencia.json",
        output_dir.parent / "relatorio_conferencia.json",
        Path("output") / "relatorio_conferencia.json",
    ]

    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return None

    return None


def _extract_atas_from_report(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report:
        return []

    atas = report.get("atas") or report.get("fornecedores") or []
    result = []

    for ata in atas:
        nome = (
            ata.get("fornecedor_nome")
            or ata.get("razao_social")
            or ata.get("nome")
            or ata.get("fornecedor")
            or ata.get("contratado")
            or ""
        )

        itens = ata.get("itens") or []
        item_nums = []
        valor_total = 0.0

        for item in itens:
            if isinstance(item, dict):
                n = (
                    item.get("numero_item")
                    or item.get("item")
                    or item.get("codigo")
                    or item.get("numero")
                )

                if n is not None:
                    try:
                        item_nums.append(str(int(n)).zfill(4))
                    except Exception:
                        item_nums.append(str(n).zfill(4))

                valor_total += _money(
                    item.get("valor_total")
                    or item.get("valor")
                    or item.get("total")
                    or item.get("valor_total_pdf")
                )
            else:
                try:
                    item_nums.append(str(int(item)).zfill(4))
                except Exception:
                    item_nums.append(str(item).zfill(4))

        result.append({
            "nome": nome,
            "key": _supplier_key(nome),
            "short_key": _short_key(nome),
            "itens": sorted(set(item_nums)),
            "valor_total": valor_total,
        })

    return result


def _parse_pdf_again(pdf_path: Path) -> list[dict[str, Any]]:
    try:
        from licitasuite.parsers.pdf_winners_parser import PdfWinnersParser
    except Exception:
        return []

    fornecedores = PdfWinnersParser().parse(pdf_path)
    rows = []

    for f in fornecedores:
        nome = getattr(f, "razao_social", "") or getattr(f, "nome", "")
        itens = []
        valor = 0.0

        for item in getattr(f, "itens", []) or []:
            n = getattr(item, "numero_item", None)

            if n is not None:
                try:
                    itens.append(str(int(n)).zfill(4))
                except Exception:
                    itens.append(str(n).zfill(4))

            valor += _money(getattr(item, "valor_total", 0))

        rows.append({
            "nome": nome,
            "key": _supplier_key(nome),
            "short_key": _short_key(nome),
            "itens": sorted(set(itens)),
            "valor_total": valor,
        })

    return rows


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


def _docx_rows(docx_files: list[Path]) -> list[dict[str, Any]]:
    rows = []

    for file in docx_files:
        stem = file.stem

        # Remove o prefixo "ATA DE REGISTRO ... - "
        if " - " in stem:
            nome = stem.split(" - ", 1)[1]
        else:
            nome = stem

        rows.append({
            "arquivo": file.name,
            "nome": nome,
            "key": _supplier_key(nome),
            "short_key": _short_key(nome),
        })

    return rows


def _match_by_key(source_rows: list[dict[str, Any]], target_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Faz correspondência tolerante:
    1. key completa;
    2. short_key;
    3. inclusão parcial.
    """
    matched = {}

    target_by_key = {r["key"]: r for r in target_rows if r.get("key")}
    target_by_short = {r["short_key"]: r for r in target_rows if r.get("short_key")}

    for src in source_rows:
        key = src.get("key", "")
        short = src.get("short_key", "")

        found = None

        if key in target_by_key:
            found = target_by_key[key]
        elif short in target_by_short:
            found = target_by_short[short]
        else:
            for tgt in target_rows:
                tk = tgt.get("key", "")
                if key and tk and (key in tk or tk in key):
                    found = tgt
                    break
                if short and tk and short in tk:
                    found = tgt
                    break

        if found:
            matched[key] = found

    return matched


def build_conferencia(zip_path: Path | None, output_dir: Path, docx_files: list[Path]) -> dict[str, Any]:
    pdf_path = _find_pdf_in_zip_or_folder(zip_path)
    pdf_rows = _parse_pdf_again(pdf_path) if pdf_path else []

    report = _read_relatorio_json(output_dir)
    ata_rows = _extract_atas_from_report(report)
    docx_rows = _docx_rows(docx_files)

    docx_match = _match_by_key(pdf_rows, docx_rows)
    ata_match = _match_by_key(pdf_rows, ata_rows)

    faltando_docx = []
    faltando_relatorio = []

    divergencias_valor = []
    divergencias_itens = []

    for pdf in pdf_rows:
        key = pdf["key"]

        docx = docx_match.get(key)
        ata = ata_match.get(key)

        if not docx:
            faltando_docx.append(pdf["nome"])

        if not ata:
            faltando_relatorio.append(pdf["nome"])
            continue

        pdf_v = pdf["valor_total"]
        ata_v = ata["valor_total"]

        if abs(pdf_v - ata_v) > 0.05:
            divergencias_valor.append({
                "fornecedor": pdf["nome"],
                "valor_pdf": pdf_v,
                "valor_ata": ata_v,
                "diferenca": ata_v - pdf_v,
            })

        pdf_itens = set(pdf["itens"])
        ata_itens = set(ata["itens"])

        if pdf_itens != ata_itens:
            divergencias_itens.append({
                "fornecedor": pdf["nome"],
                "itens_pdf": sorted(pdf_itens),
                "itens_ata": sorted(ata_itens),
                "faltando_na_ata": sorted(pdf_itens - ata_itens),
                "sobrando_na_ata": sorted(ata_itens - pdf_itens),
            })

    return {
        "pdf_path": str(pdf_path) if pdf_path else "",
        "total_fornecedores_pdf": len(pdf_rows),
        "total_fornecedores_relatorio": len(ata_rows),
        "total_docx": len(docx_files),
        "total_itens_pdf": sum(len(r["itens"]) for r in pdf_rows),
        "total_itens_relatorio": sum(len(r["itens"]) for r in ata_rows),
        "valor_total_pdf_lido": sum(r["valor_total"] for r in pdf_rows),
        "valor_total_atas": sum(r["valor_total"] for r in ata_rows),
        "faltando_docx": faltando_docx,
        "faltando_relatorio": faltando_relatorio,
        "divergencias_valor": divergencias_valor,
        "divergencias_itens": divergencias_itens,
        "ok": not faltando_docx and not faltando_relatorio and not divergencias_valor and not divergencias_itens,
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
        ["Conferência automática", ""],
        ["PDF usado", conferencia.get("pdf_path", "")],
        ["Fornecedores no PDF", conferencia.get("total_fornecedores_pdf", 0)],
        ["Fornecedores no relatório", conferencia.get("total_fornecedores_relatorio", 0)],
        ["Arquivos DOCX gerados", conferencia.get("total_docx", 0)],
        ["Itens no PDF", conferencia.get("total_itens_pdf", 0)],
        ["Itens nas atas", conferencia.get("total_itens_relatorio", 0)],
        ["Valor total PDF lido", _fmt_money(conferencia.get("valor_total_pdf_lido", 0))],
        ["Valor total atas", _fmt_money(conferencia.get("valor_total_atas", 0))],
        ["Status", "OK" if conferencia.get("ok") else "VERIFICAR PENDÊNCIAS"],
    ]

    for row in rows:
        ws.append(row)

    ws["A1"].font = Font(bold=True, size=15, color="073F9E")
    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 95

    red_fill = PatternFill("solid", fgColor="F8D7DA")
    green_fill = PatternFill("solid", fgColor="D9EAD3")
    blue_fill = PatternFill("solid", fgColor="073F9E")
    white_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="D9E2F3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["B10"].fill = green_fill if conferencia.get("ok") else red_fill

    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = border

    def create_sheet(name, headers, data_rows):
        sh = wb.create_sheet(name)
        sh.append(headers)

        for cell in sh[1]:
            cell.font = white_font
            cell.fill = blue_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border

        for row in data_rows:
            sh.append(row)

        for row in sh.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                cell.border = border

        for col in range(1, len(headers) + 1):
            sh.column_dimensions[chr(64 + col)].width = 38

        sh.freeze_panes = "A2"
        sh.auto_filter.ref = sh.dimensions

    create_sheet(
        "Fornecedores faltantes",
        ["Tipo", "Fornecedor"],
        [["Sem DOCX", x] for x in conferencia.get("faltando_docx", [])]
        + [["Sem relatório JSON", x] for x in conferencia.get("faltando_relatorio", [])],
    )

    create_sheet(
        "Divergência de valores",
        ["Fornecedor", "Valor PDF", "Valor Ata", "Diferença"],
        [
            [
                d["fornecedor"],
                _fmt_money(d["valor_pdf"]),
                _fmt_money(d["valor_ata"]),
                _fmt_money(d["diferenca"]),
            ]
            for d in conferencia.get("divergencias_valor", [])
        ],
    )

    create_sheet(
        "Divergência de itens",
        ["Fornecedor", "Itens PDF", "Itens Ata", "Faltando na Ata", "Sobrando na Ata"],
        [
            [
                d["fornecedor"],
                ", ".join(d["itens_pdf"]),
                ", ".join(d["itens_ata"]),
                ", ".join(d["faltando_na_ata"]),
                ", ".join(d["sobrando_na_ata"]),
            ]
            for d in conferencia.get("divergencias_itens", [])
        ],
    )

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
            "✅ Conferência automática OK\n\n"
            f"- Fornecedores no PDF: **{conferencia.get('total_fornecedores_pdf', 0)}**\n"
            f"- DOCX gerados: **{conferencia.get('total_docx', 0)}**\n"
            f"- Itens no PDF: **{conferencia.get('total_itens_pdf', 0)}**\n"
            f"- Itens nas atas: **{conferencia.get('total_itens_relatorio', 0)}**\n"
            f"- Valor PDF: **{_fmt_money(conferencia.get('valor_total_pdf_lido', 0))}**\n"
            f"- Valor atas: **{_fmt_money(conferencia.get('valor_total_atas', 0))}**"
        )

    parts = [
        "⚠️ Conferência automática encontrou pendências",
        "",
        f"- Fornecedores no PDF: **{conferencia.get('total_fornecedores_pdf', 0)}**",
        f"- DOCX gerados: **{conferencia.get('total_docx', 0)}**",
        f"- Itens no PDF: **{conferencia.get('total_itens_pdf', 0)}**",
        f"- Itens nas atas: **{conferencia.get('total_itens_relatorio', 0)}**",
        f"- Valor PDF: **{_fmt_money(conferencia.get('valor_total_pdf_lido', 0))}**",
        f"- Valor atas: **{_fmt_money(conferencia.get('valor_total_atas', 0))}",
    ]

    if conferencia.get("faltando_docx"):
        parts.append("")
        parts.append("**Fornecedores sem DOCX:**")
        for x in conferencia["faltando_docx"][:12]:
            parts.append(f"- {x}")

    if conferencia.get("divergencias_valor"):
        parts.append("")
        parts.append("**Divergências de valor:**")
        for d in conferencia["divergencias_valor"][:12]:
            parts.append(
                f"- {d['fornecedor']}: PDF {_fmt_money(d['valor_pdf'])} | Ata {_fmt_money(d['valor_ata'])}"
            )

    if conferencia.get("divergencias_itens"):
        parts.append("")
        parts.append("**Divergências de itens:**")
        for d in conferencia["divergencias_itens"][:12]:
            parts.append(f"- {d['fornecedor']}")

    return "\n".join(parts)
