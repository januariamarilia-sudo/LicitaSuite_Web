from pathlib import Path
import re
import shutil
import sys


ROOT = Path.cwd()
ROBUST_SRC = ROOT / "licitasuite" / "parsers" / "vencedores_pdf_robusto.py"


ROBUST_CODE = r"""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import re
import tempfile
from typing import Any


def _read_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader
        except Exception as exc:
            raise RuntimeError("Instale pypdf ou PyPDF2 para ler o PDF dos vencedores.") from exc

    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n".join(pages)


def _extract_pdf_from_zip(zip_path: Path) -> Path | None:
    temp_dir = Path(tempfile.mkdtemp(prefix="licitasuite_vencedores_"))

    with ZipFile(zip_path, "r") as z:
        pdf_names = [n for n in z.namelist() if n.lower().endswith(".pdf")]
        if not pdf_names:
            return None

        pdf_names.sort(key=lambda n: (0 if "venced" in n.lower() else 1, len(n)))

        for name in pdf_names:
            out = temp_dir / Path(name).name
            out.write_bytes(z.read(name))
            try:
                txt = _read_pdf_text(out).upper()
                if "VENCEDORES DO PROCESSO" in txt or "TOTAL DO VENCEDOR" in txt:
                    return out
            except Exception:
                continue

        out = temp_dir / Path(pdf_names[0]).name
        out.write_bytes(z.read(pdf_names[0]))
        return out


def _money_to_float(value: str) -> float:
    value = (value or "").replace("R$", "").strip()
    value = value.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except Exception:
        return 0.0


def _first_money_after(text: str, start: int) -> str:
    trecho = text[start:start + 350]
    m = re.search(r"R\$\s*([0-9\.\,]+)", trecho)
    return ("R$ " + m.group(1)) if m else ""


def _normalize_block(block: str) -> str:
    block = block.replace("\xa0", " ")
    block = block.replace("\u00ad", "")
    block = re.sub(r"[ \t]+", " ", block)
    block = re.sub(r"\n{3,}", "\n\n", block)
    return block


def _item_starts(block: str) -> list[re.Match]:
    return list(re.finditer(r"(?m)^([0-9]{4})\s+(.+)", block))


def _parse_item(block: str, item_match: re.Match, next_start: int | None) -> dict[str, Any]:
    codigo = item_match.group(1)
    inicio = item_match.start()
    fim = next_start if next_start is not None else len(block)
    trecho = block[inicio:fim]

    linhas = [l.strip() for l in trecho.splitlines() if l.strip()]
    descricao = " ".join(linhas[:3])
    descricao = re.sub(r"^[0-9]{4}\s+", "", descricao).strip()

    money_values = re.findall(r"R\$\s*([0-9\.\,]+)", trecho)
    valor_unitario = "R$ " + money_values[-2] if len(money_values) >= 2 else ""
    valor_total = "R$ " + money_values[-1] if money_values else ""

    qtd = ""
    unidade = ""
    # Captura padrão: 3.570.497 CPR R$
    m_qtd = re.search(r"([0-9]{1,3}(?:\.[0-9]{3})*|[0-9]+)\s+([A-Z]{2,5})\s+R\$", trecho)
    if m_qtd:
        qtd = m_qtd.group(1)
        unidade = m_qtd.group(2)

    marca = ""
    modelo = ""
    # heurística simples: linhas entre descrição e quantidade
    if m_qtd:
        antes_qtd = trecho[:m_qtd.start()]
        partes = [l.strip() for l in antes_qtd.splitlines() if l.strip()]
        partes = [re.sub(r"^[0-9]{4}\s+", "", p).strip() for p in partes]
        if len(partes) >= 4:
            modelo = partes[-2]
            marca = partes[-1]
        elif len(partes) >= 2:
            marca = partes[-1]

    return {
        "codigo": codigo,
        "item": codigo.lstrip("0") or codigo,
        "descricao": descricao,
        "produto": descricao,
        "modelo": modelo,
        "marca": marca,
        "fabricante": marca,
        "qtde": qtd,
        "quantidade": qtd,
        "unidade": unidade,
        "valor_unitario": valor_unitario,
        "valor_total": valor_total,
        "valor_total_num": _money_to_float(valor_total),
    }


def parse_vencedores_pdf_text(text: str) -> list[dict[str, Any]]:
    \"\"\"
    Parser robusto para o PDF 'Vencedores do Processo' do Portal de Compras Públicas.

    Diferencial:
    - não depende de 'TOTAL DO VENCEDOR' para achar o início do fornecedor;
    - identifica fornecedor por linha contendo '| Tipo:';
    - suporta fornecedor dividido entre páginas;
    - retorna todos os blocos encontrados no PDF.
    \"\"\"
    text = _normalize_block(text or "")

    headers = list(re.finditer(r"(?m)^(.+?)\s+\|\s*Tipo:", text, flags=re.I))
    vencedores: list[dict[str, Any]] = []

    for i, h in enumerate(headers):
        nome = re.sub(r"\s+", " ", h.group(1)).strip()
        start = h.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        bloco = text[start:end]

        cnpj = ""
        cnpj_m = re.search(
            r"Documento\s+([0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})",
            bloco,
            flags=re.I,
        )
        if cnpj_m:
            cnpj = cnpj_m.group(1)

        total = ""
        total_m = re.search(r"TOTAL\s+DO\s+VENCEDOR\s+R\$\s*([0-9\.\,]+)", bloco, flags=re.I)
        if total_m:
            total = "R$ " + total_m.group(1)

        starts = _item_starts(bloco)
        itens = []
        for j, im in enumerate(starts):
            next_start = starts[j + 1].start() if j + 1 < len(starts) else None
            item = _parse_item(bloco, im, next_start)
            itens.append(item)

        vencedores.append({
            "nome": nome,
            "fornecedor": nome,
            "contratado": nome,
            "cnpj": cnpj,
            "documento": cnpj,
            "itens": itens,
            "itens_numeros": [it["item"] for it in itens],
            "valor_total": total,
            "total": total,
            "valor_total_num": _money_to_float(total),
            "observacoes": [],
        })

    return vencedores


def parse_vencedores_pdf(path_or_text: Any, *args, **kwargs) -> list[dict[str, Any]]:
    \"\"\"
    Aceita caminho de PDF, ZIP ou texto já extraído.
    \"\"\"
    if path_or_text is None:
        return []

    if isinstance(path_or_text, (str, Path)):
        p = Path(str(path_or_text))
        if p.exists() and p.suffix.lower() == ".zip":
            pdf = _extract_pdf_from_zip(p)
            if not pdf:
                return []
            return parse_vencedores_pdf(pdf)
        if p.exists() and p.suffix.lower() == ".pdf":
            return parse_vencedores_pdf_text(_read_pdf_text(p))

        # se não existir como arquivo, trata como texto
        return parse_vencedores_pdf_text(str(path_or_text))

    return []


# Aliases para compatibilidade com nomes comuns usados no motor.
def extrair_vencedores_pdf(*args, **kwargs):
    return parse_vencedores_pdf(*args, **kwargs)

def extrair_vencedores(*args, **kwargs):
    return parse_vencedores_pdf(*args, **kwargs)

def parse_pdf_vencedores(*args, **kwargs):
    return parse_vencedores_pdf(*args, **kwargs)

def parse_vencedores(*args, **kwargs):
    return parse_vencedores_pdf(*args, **kwargs)

def ler_vencedores_pdf(*args, **kwargs):
    return parse_vencedores_pdf(*args, **kwargs)
"""


def write_robust_parser():
    ROBUST_SRC.parent.mkdir(parents=True, exist_ok=True)
    ROBUST_SRC.write_text(ROBUST_CODE, encoding="utf-8")
    print(f"OK: parser robusto criado em {ROBUST_SRC}")


def find_candidate_files():
    candidates = []
    for path in (ROOT / "licitasuite").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        name = path.name.lower()
        score = 0

        if "TOTAL DO VENCEDOR" in text:
            score += 10
        if "VENCEDORES DO PROCESSO" in text:
            score += 10
        if "item(ns)" in text:
            score += 4
        if "venced" in name:
            score += 8
        if "venced" in text.lower():
            score += 4
        if "pdf" in name:
            score += 2
        if score:
            candidates.append((score, path, text))

    candidates.sort(reverse=True, key=lambda x: x[0])
    return candidates


def append_wrappers(path: Path, text: str):
    backup = path.with_suffix(path.suffix + ".bak_vencedores_24")
    if not backup.exists():
        shutil.copy2(path, backup)

    funcs = re.findall(r"(?m)^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", text)

    target_funcs = []
    for fn in funcs:
        low = fn.lower()
        if "venced" in low:
            target_funcs.append(fn)

    if not target_funcs:
        # Só aplica em arquivo muito claramente de vencedores
        if "venced" in path.name.lower():
            target_funcs = funcs[:]
        else:
            return False, []

    unique = []
    for fn in target_funcs:
        if fn not in unique:
            unique.append(fn)

    patch = [
        "",
        "",
        "# === PATCH LICITASUITE 2.1 — PARSER ROBUSTO DE VENCEDORES ===",
        "# Este bloco sobrescreve as funções antigas de leitura de vencedores.",
        "try:",
        "    from licitasuite.parsers.vencedores_pdf_robusto import parse_vencedores_pdf as _licitasuite_parse_vencedores_pdf_robusto",
    ]

    for fn in unique:
        patch.extend([
            f"    def {fn}(*args, **kwargs):",
            f"        return _licitasuite_parse_vencedores_pdf_robusto(*args, **kwargs)",
        ])

    patch.extend([
        "except Exception as _licitasuite_patch_exc:",
        "    pass",
        "# === FIM DO PATCH LICITASUITE 2.1 ===",
        "",
    ])

    path.write_text(text.rstrip() + "\n" + "\n".join(patch), encoding="utf-8")
    return True, unique


def main():
    write_robust_parser()

    candidates = find_candidate_files()

    if not candidates:
        print("ATENÇÃO: não encontrei automaticamente o arquivo antigo do parser.")
        print("O parser robusto foi criado, mas talvez seja necessário ajustar o import no motor.")
        return

    print("Candidatos encontrados:")
    for score, path, _ in candidates[:8]:
        print(f" - score {score}: {path.relative_to(ROOT)}")

    applied = []
    for score, path, text in candidates:
        # Evita mexer em arquivos muito genéricos.
        if score < 8:
            continue
        ok, funcs = append_wrappers(path, text)
        if ok:
            applied.append((path, funcs))

    if not applied:
        print("ATENÇÃO: parser robusto criado, mas nenhum arquivo antigo foi alterado.")
        print("Me envie o resultado de: grep -R \"def .*venced\" licitasuite -n")
        return

    print("")
    print("PATCH APLICADO COM SUCESSO em:")
    for path, funcs in applied:
        print(f" - {path.relative_to(ROOT)} -> funções: {', '.join(funcs)}")

    print("")
    print("Agora rode:")
    print("git add licitasuite/parsers/vencedores_pdf_robusto.py licitasuite")
    print('git commit -m "Corrige parser de vencedores para 24 fornecedores"')
    print("git push")


if __name__ == "__main__":
    main()
