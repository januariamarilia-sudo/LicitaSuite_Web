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
    text = str(value).replace("R$", "").strip()
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        return 0.0


def _fmt_money(value: float) -> str:
    return "R$ " + f"{float(value):,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _norm(value: Any) -> str:
    text = str(value or "").upper()
    repl = {
        "Á": "A", "À": "A", "Â": "A", "Ã": "A",
        "É": "E", "Ê": "E", "Í": "I",
        "Ó": "O", "Ô": "O", "Õ": "O",
        "Ú": "U", "Ç": "C",
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _supplier_key(name: str) -> str:
    text = _norm(name)
    remove = {
        "LTDA", "EIRELI", "S", "A", "SA", "ME", "EPP", "SS",
        "COMERCIO", "DISTRIBUIDORA", "DISTRIBUICAO",
        "MEDICAMENTOS", "PRODUTOS", "HOSPITALARES",
        "IMPORTACAO", "EXPORTACAO", "SERVICOS", "FARMACEUTICA",
    }
    tokens = [t for t in text.split() if t not in remove]
    return " ".join(tokens[:4])


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
                n = item.get("numero_item") or item.get("item") or item.get("codigo")
                if n is not None:
                    item_nums.append(str(n).zfill(4))
                valor_total += _money(item.get("valor_total") or item.get("total") or item.get("valor_total_pdf"))
            else:
                item_nums.append(str(item).zfill(4))

        result.append({
            "nome": nome,
            "key": _supplier_key(nome),
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
                itens.append(str(n).zfill(4))
            valor += _money(getattr(item, "valor_total", 0))

        rows.append({
            "nome": nome,
            "key": _supplier_key(nome),
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
        nome = re.sub(r"^.*?\s-\s", "", stem).strip()
        rows.append({
            "arquivo": file.name,
            "nome": nome,
            "key": _supplier_key(nome),
        })
    return rows


def build_conferencia(zip_path: Path | None, output_dir: Path, docx_files: list[Path]) -> dict[str, Any]:
    pdf_path = _find_pdf_in_zip_or_folder(zip_path)
    pdf_rows = _parse_pdf_again(pdf_path) if pdf_path else []

    report = _read_relatorio_json(output_dir)
    ata_rows = _extract_atas_from_report(report)
    docx = _docx_rows(docx_files)

    pdf_by_key = {r["key"]: r for r in pdf_rows if r["key"]}
    ata_by_key = {r["key"]: r for r in ata_rows if r["key"]}
    docx_by_key = {r["key"]: r for r in docx if r["key"]}

    faltando_docx = sorted(set(pdf_by_key) - set(docx_by_key))
    faltando_relatorio = sorted(set(pdf_by_key) - set(ata_by_key))

    divergencias_valor = []
    for key in sorted(set(pdf_by_key) & set(ata_by_key)):
        pdf_v = pdf_by_key[key]["valor_total"]
        ata_v = ata_by_key[key]["valor_total"]
        if abs(pdf_v - ata_v) > 0.05:
            divergencias_valor.append({
                "fornecedor": pdf_by_key[key]["nome"],
                "valor_pdf": pdf_v,
                "valor_ata": ata_v,
                "diferenca": ata_v - pdf_v,
            })

    divergencias_itens = []
    for key in sorted(set(pdf_by_key) & set(ata_by_key)):
        pdf_itens = set(pdf_by_key[key]["itens"])
        ata_itens = set(ata_by_key[key]["itens"])
        if pdf_itens != ata_itens:
            divergencias_itens.append({
                "fornecedor": pdf_by_key[key]["nome"],
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
        "faltando_docx": [pdf_by_key[k]["nome"] for k in faltando_docx if k in pdf_by_key],
        "faltando_relatorio": [pdf_by_key[k]["nome"] for k in faltando_relatorio if k in pdf_by_key],
        "divergencias_valor": divergencias_valor,
        "divergencias_itens": divergencias_itens,
        "ok": not faltando_docx and not faltando_relatorio and not divergencias_valor and not divergencias_itens,
    }


def write_conferencia_xlsx(conferencia: dict[str, Any], output_dir: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

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
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 90

    red_fill = PatternFill("solid", fgColor="F8D7DA")
    green_fill = PatternFill("solid", fgColor="D9EAD3")
    ws["B10"].fill = green_fill if conferencia.get("ok") else red_fill

    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    def create_sheet(name, headers, data_rows):
        sh = wb.create_sheet(name)
        sh.append(headers)
        for cell in sh[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="073F9E")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for row in data_rows:
            sh.append(row)

        for col in range(1, len(headers) + 1):
            sh.column_dimensions[chr(64 + col)].width = 38

        for row in sh.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    create_sheet(
        "Fornecedores faltantes",
        ["Tipo", "Fornecedor"],
        [["Sem DOCX", x] for x in conferencia.get("faltando_docx", [])]
        + [["Sem relatório", x] for x in conferencia.get("faltando_relatorio", [])],
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
        f"- Valor atas: **{_fmt_money(conferencia.get('valor_total_atas', 0))}**",
    ]

    if conferencia.get("faltando_docx"):
        parts.append("")
        parts.append("**Fornecedores sem DOCX:**")
        for x in conferencia["faltando_docx"]:
            parts.append(f"- {x}")

    if conferencia.get("divergencias_valor"):
        parts.append("")
        parts.append("**Divergências de valor:**")
        for d in conferencia["divergencias_valor"][:10]:
            parts.append(f"- {d['fornecedor']}: PDF {_fmt_money(d['valor_pdf'])} | Ata {_fmt_money(d['valor_ata'])}")

    if conferencia.get("divergencias_itens"):
        parts.append("")
        parts.append("**Divergências de itens:**")
        for d in conferencia["divergencias_itens"][:10]:
            parts.append(f"- {d['fornecedor']}")

    return "\n".join(parts)
