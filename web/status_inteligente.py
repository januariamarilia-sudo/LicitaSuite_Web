from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import re
from typing import Any

from web.validador_vencedores import parse_vencedores_pdf, extract_pdf_from_zip


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


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


def build_status_data(result: Any, output_dir: Path, docx_files: list[Path], zip_path: Path | None = None) -> dict[str, Any]:
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

    # Fallback mais confiável: PDF dos vencedores dentro do ZIP
    if not fornecedores and zip_path:
        try:
            pdf_path = extract_pdf_from_zip(zip_path)
            if pdf_path:
                fornecedores = parse_vencedores_pdf(pdf_path)
        except Exception as exc:
            observacoes_gerais.append(f"Não foi possível montar prévia pelo PDF: {exc}")

    total_itens = 0
    for f in fornecedores:
        itens = f.get("itens", [])
        if isinstance(itens, list):
            total_itens += len(itens)
        f.setdefault("observacoes", [])
        f.setdefault("arquivo_gerado", "")

    return {
        "messages": messages,
        "errors": errors,
        "fornecedores": fornecedores,
        "itens_sem_vencedor": itens_sem_vencedor,
        "observacoes_gerais": observacoes_gerais,
        "process_info": {},
        "total_atas": len(docx_files),
        "total_itens": total_itens,
        "total_itens_nao_localizados": len(itens_sem_vencedor),
    }


def create_control_workbook(status_data: dict[str, Any], output_dir: Path) -> Path:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    except Exception as exc:
        raise RuntimeError("Para gerar a planilha de controle, inclua openpyxl no requirements.txt.") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "CONTROLE DE NUMERAÇÃO - PL ATUAL.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Controle"

    headers = [
        "Nº", "TIPO", "OBJETO", "PL", "MODALIDADE", "CONTRATADO",
        "VALOR TOTAL", "QTDE ITENS", "ITENS", "ARQUIVO GERADO", "OBSERVAÇÃO"
    ]
    ws.append(headers)

    fill = PatternFill("solid", fgColor="073F9E")
    font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="D9E2F3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for idx, f in enumerate(status_data.get("fornecedores", []), start=1):
        itens = f.get("itens", [])
        itens_texto = ", ".join(str(i) for i in itens) if isinstance(itens, list) else str(itens or "")
        valor = f.get("valor_total") or f.get("valor") or ""
        obs = f.get("observacoes") or ""
        if isinstance(obs, list):
            obs = " | ".join(str(o) for o in obs)

        ws.append([
            idx,
            "ATA",
            "",
            "",
            "",
            f.get("nome") or f.get("fornecedor") or f.get("contratado") or "",
            valor,
            len(itens) if isinstance(itens, list) else "",
            itens_texto,
            f.get("arquivo_gerado") or "",
            obs,
        ])

    widths = [8, 12, 34, 16, 16, 42, 18, 13, 34, 52, 45]
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[chr(64+i)].width = width

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

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
