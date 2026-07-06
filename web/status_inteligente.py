from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import re
from typing import Any


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _format_pl_pe(value: str) -> str:
    value = _safe_text(value)
    return value.replace("/", ".")


def _extract_from_text(text: str, pattern: str, default: str = "") -> str:
    m = re.search(pattern, text or "", flags=re.I)
    return m.group(1).strip() if m else default


def _discover_process_info(messages: list[str], relatorio: dict[str, Any] | None = None) -> dict[str, str]:
    joined = "\n".join(messages or [])

    pl = _extract_from_text(joined, r"PL\s*([0-9]+[./][0-9]{4})")
    pe = _extract_from_text(joined, r"PE\s*([0-9]+[./][0-9]{4})")

    # fallback em textos do motor
    if not pl:
        pl = _extract_from_text(joined, r"PROCESSO LICITAT[ÓO]RIO\s*N[º°]?\s*([0-9]+[./][0-9]{4})")
    if not pe:
        pe = _extract_from_text(joined, r"PREG[ÃA]O ELETR[ÔO]NICO\s*N[º°]?\s*([0-9]+[./][0-9]{4})")

    return {
        "pl": f"PL {pl}" if pl and not pl.upper().startswith("PL") else pl,
        "pe": f"PE {pe}" if pe and not pe.upper().startswith("PE") else pe,
        "pl_file": _format_pl_pe(pl),
        "pe_file": _format_pl_pe(pe),
    }


def load_report(output_dir: Path) -> dict[str, Any] | None:
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


def build_status_data(result: Any, output_dir: Path, docx_files: list[Path]) -> dict[str, Any]:
    messages = list(getattr(result, "messages", []) or [])
    errors = list(getattr(result, "errors", []) or [])
    report = load_report(output_dir)

    fornecedores = []
    itens_sem_vencedor = []
    observacoes_gerais = []

    if report:
        fornecedores = report.get("fornecedores", []) or report.get("atas", []) or []
        itens_sem_vencedor = report.get("itens_sem_vencedor", []) or report.get("itens_nao_localizados", []) or []
        observacoes_gerais = report.get("observacoes_gerais", []) or report.get("inconsistencias", []) or []
    else:
        # fallback simples a partir das mensagens do motor
        for msg in messages:
            m = re.search(r"-\s*(.+?):\s*([0-9]+)\s*item", msg, flags=re.I)
            if m:
                fornecedores.append({
                    "nome": m.group(1).strip(),
                    "itens": [],
                    "valor_total": "",
                    "observacoes": [],
                })

    process_info = _discover_process_info(messages, report)

    # relaciona arquivos docx aos fornecedores quando possível
    for f in fornecedores:
        nome = _safe_text(f.get("nome") or f.get("fornecedor") or f.get("contratado"))
        f["nome"] = nome
        f.setdefault("itens", [])
        f.setdefault("observacoes", [])
        f.setdefault("arquivo_gerado", "")

        if not f["arquivo_gerado"]:
            nome_norm = re.sub(r"\W+", "", nome.upper())
            for docx in docx_files:
                docx_norm = re.sub(r"\W+", "", docx.stem.upper())
                if nome_norm and (nome_norm[:12] in docx_norm or docx_norm[:12] in nome_norm):
                    f["arquivo_gerado"] = docx.name
                    break

        if not f["arquivo_gerado"] and docx_files:
            idx = fornecedores.index(f)
            if idx < len(docx_files):
                f["arquivo_gerado"] = docx_files[idx].name

    total_itens = 0
    for f in fornecedores:
        itens = f.get("itens", [])
        if isinstance(itens, list):
            total_itens += len(itens)

    return {
        "messages": messages,
        "errors": errors,
        "fornecedores": fornecedores,
        "itens_sem_vencedor": itens_sem_vencedor,
        "observacoes_gerais": observacoes_gerais,
        "process_info": process_info,
        "total_atas": len(docx_files) if docx_files else len(fornecedores),
        "total_itens": total_itens,
        "total_itens_nao_localizados": len(itens_sem_vencedor),
    }


def create_control_workbook(status_data: dict[str, Any], output_dir: Path) -> Path:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
        from openpyxl.utils import get_column_letter
    except Exception as exc:
        raise RuntimeError("Para gerar a planilha de controle, inclua openpyxl no requirements.txt.") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    info = status_data.get("process_info", {})
    pl_file = info.get("pl_file") or "XX.2026"
    pe_file = info.get("pe_file") or "XX.2026"

    out = output_dir / f"CONTROLE DE NUMERAÇÃO - PL {pl_file} PE {pe_file}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Controle"

    headers = [
        "Nº",
        "TIPO",
        "OBJETO",
        "PL",
        "MODALIDADE",
        "CONTRATADO",
        "VALOR TOTAL",
        "QTDE ITENS",
        "ITENS",
        "ARQUIVO GERADO",
        "OBSERVAÇÃO",
    ]

    ws.append(headers)

    header_fill = PatternFill("solid", fgColor="073F9E")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="D9E2F3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    fornecedores = status_data.get("fornecedores", [])
    pl = info.get("pl") or ""
    pe = info.get("pe") or ""

    for idx, fornecedor in enumerate(fornecedores, start=1):
        itens = fornecedor.get("itens", [])
        if isinstance(itens, list):
            itens_texto = ", ".join(str(i) for i in itens)
            qtde = len(itens)
        else:
            itens_texto = str(itens)
            qtde = ""

        observacoes = fornecedor.get("observacoes", []) or fornecedor.get("inconsistencias", [])
        if isinstance(observacoes, list):
            observacao = " | ".join(str(o) for o in observacoes)
        else:
            observacao = str(observacoes or "")

        ws.append([
            idx,
            "ATA",
            "",
            pl,
            pe,
            fornecedor.get("nome") or fornecedor.get("fornecedor") or fornecedor.get("contratado") or "",
            fornecedor.get("valor_total") or fornecedor.get("valor") or "",
            qtde,
            itens_texto,
            fornecedor.get("arquivo_gerado") or "",
            observacao,
        ])

    # Formatação
    widths = {
        "A": 8,
        "B": 12,
        "C": 34,
        "D": 16,
        "E": 16,
        "F": 34,
        "G": 18,
        "H": 13,
        "I": 30,
        "J": 48,
        "K": 42,
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        row[0].alignment = Alignment(horizontal="center", vertical="top")
        row[7].alignment = Alignment(horizontal="center", vertical="top")

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    # Aba resumo
    resumo = wb.create_sheet("Resumo")
    resumo.append(["Resumo da Geração"])
    resumo["A1"].font = Font(bold=True, size=16, color="073F9E")
    resumo.append(["PL", pl])
    resumo.append(["Modalidade", pe])
    resumo.append(["Total de atas", status_data.get("total_atas", 0)])
    resumo.append(["Total de itens processados", status_data.get("total_itens", 0)])
    resumo.append(["Itens não localizados", ", ".join(str(i) for i in status_data.get("itens_sem_vencedor", []))])
    resumo.append(["Observações gerais", " | ".join(str(o) for o in status_data.get("observacoes_gerais", []))])
    resumo.column_dimensions["A"].width = 28
    resumo.column_dimensions["B"].width = 90

    for row in resumo.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    wb.save(out)
    return out


def add_extra_files_to_zip(zip_path: Path, extra_files: list[Path]) -> Path:
    if not extra_files:
        return zip_path

    tmp = zip_path.with_suffix(".tmp.zip")

    with ZipFile(zip_path, "r") as zin:
        existing = {item.filename for item in zin.infolist()}
        with ZipFile(tmp, "w", ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))

            for file in extra_files:
                if file.exists() and file.name not in existing:
                    zout.write(file, file.name)

    tmp.replace(zip_path)
    return zip_path
