from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from zipfile import ZipFile
import re
import tempfile
from typing import Any


@dataclass
class VencedorPDF:
    nome: str
    cnpj: str = ""
    itens: list[str] | None = None
    valor_total: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["itens"] = self.itens or []
        return d


def _norm_text(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("Á", "A").replace("À", "A").replace("Â", "A").replace("Ã", "A")
    s = s.replace("É", "E").replace("Ê", "E")
    s = s.replace("Í", "I")
    s = s.replace("Ó", "O").replace("Ô", "O").replace("Õ", "O")
    s = s.replace("Ú", "U")
    s = s.replace("Ç", "C")
    return s.strip()


def fornecedor_key(nome: str) -> str:
    nome = _norm_text(nome)
    nome = re.sub(r"\b(LTDA|EIRELI|S/A|SA|ME|EPP|SS|DEMAIS|COMERCIO|COMÉRCIO)\b", " ", nome)
    nome = re.sub(r"[^A-Z0-9]+", " ", nome)
    return re.sub(r"\s+", " ", nome).strip()


def read_pdf_text(pdf_path: Path) -> str:
    """
    Lê texto do PDF. Usa pypdf quando disponível.
    """
    try:
        from pypdf import PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader
        except Exception as exc:
            raise RuntimeError("Não foi possível ler PDF. Inclua pypdf ou PyPDF2 no requirements.txt.") from exc

    reader = PdfReader(str(pdf_path))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(parts)


def extract_pdf_from_zip(zip_path: Path) -> Path | None:
    """
    Extrai do ZIP o PDF que parece ser o relatório de vencedores.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="licitasuite_pdf_"))

    with ZipFile(zip_path, "r") as z:
        pdf_names = [n for n in z.namelist() if n.lower().endswith(".pdf")]
        if not pdf_names:
            return None

        # prioriza nome contendo vencedor
        pdf_names.sort(key=lambda n: (0 if "venced" in n.lower() else 1, len(n)))

        for name in pdf_names:
            out = temp_dir / Path(name).name
            out.write_bytes(z.read(name))
            try:
                txt = read_pdf_text(out)
                if "VENCEDORES DO PROCESSO" in txt.upper() or "TOTAL DO VENCEDOR" in txt.upper():
                    return out
            except Exception:
                continue

        # fallback: primeiro PDF
        name = pdf_names[0]
        out = temp_dir / Path(name).name
        out.write_bytes(z.read(name))
        return out


def parse_vencedores_pdf_text(text: str) -> list[VencedorPDF]:
    """
    Parser robusto para o relatório 'Vencedores do Processo' do Portal de Compras Públicas.

    Regra principal:
    - cada bloco de fornecedor começa antes de '| Tipo:'
    - cada bloco termina antes do próximo fornecedor ou antes do 'Valor Total:'
    - itens são códigos de 4 dígitos dentro do bloco
    - valor oficial é a linha 'TOTAL DO VENCEDOR R$ ...'
    """
    text = text or ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Marca fornecedores por linha que contenha "| Tipo:"
    header_re = re.compile(
        r"(?P<nome>[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ0-9][^\n|]{2,}?)\s*\|\s*Tipo:\s*(?P<resto>.*?)(?=\nCódigo\s+Produto|\n[0-9]{4}\s+|$)",
        flags=re.I | re.S,
    )

    matches = list(header_re.finditer(text))
    vencedores: list[VencedorPDF] = []

    for i, m in enumerate(matches):
        nome = re.sub(r"\s+", " ", m.group("nome")).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        bloco = text[start:end]

        cnpj = ""
        cnpj_m = re.search(r"Documento\s+([0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})", bloco)
        if cnpj_m:
            cnpj = cnpj_m.group(1)

        # Itens: captura códigos de 4 dígitos que aparecem no início de linhas ou antes de descrição.
        itens = []
        for item in re.findall(r"(?<!\d)([0-9]{4})\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ0-9]", bloco):
            if item not in itens:
                itens.append(item)

        total = ""
        total_m = re.search(r"TOTAL\s+DO\s+VENCEDOR\s+R\$\s*([0-9\.\,]+)", bloco, flags=re.I)
        if total_m:
            total = "R$ " + total_m.group(1)

        vencedores.append(VencedorPDF(nome=nome, cnpj=cnpj, itens=itens, valor_total=total))

    # fallback para PDFs cujo texto quebrou os blocos
    if not vencedores:
        nomes = re.findall(r"\n([^\n|]{3,}?)\s*\|\s*Tipo:", text, flags=re.I)
        for nome in nomes:
            vencedores.append(VencedorPDF(nome=re.sub(r"\s+", " ", nome).strip(), itens=[]))

    return vencedores


def parse_vencedores_pdf(pdf_path: Path) -> list[dict[str, Any]]:
    text = read_pdf_text(pdf_path)
    return [v.to_dict() for v in parse_vencedores_pdf_text(text)]


def vencedores_from_zip(zip_path: Path) -> list[dict[str, Any]]:
    pdf = extract_pdf_from_zip(zip_path)
    if not pdf:
        return []
    return parse_vencedores_pdf(pdf)


def compare_pdf_vs_generated(vencedores_pdf: list[dict[str, Any]], docx_files: list[Path]) -> dict[str, Any]:
    """
    Compara vencedores do PDF com nomes dos arquivos DOCX gerados.
    """
    docx_text = " ".join(p.stem for p in docx_files)
    docx_key = fornecedor_key(docx_text)

    faltantes = []
    encontrados = []

    for v in vencedores_pdf:
        nome = v.get("nome", "")
        key = fornecedor_key(nome)
        # usa as duas primeiras palavras significativas como busca
        tokens = key.split()
        probe = " ".join(tokens[:2]) if len(tokens) >= 2 else key

        if probe and probe in docx_key:
            encontrados.append(v)
        else:
            faltantes.append(v)

    return {
        "total_pdf": len(vencedores_pdf),
        "total_docx": len(docx_files),
        "faltantes": faltantes,
        "encontrados": encontrados,
    }


def format_validation_markdown(resultado: dict[str, Any]) -> str:
    faltantes = resultado.get("faltantes", [])
    total_pdf = resultado.get("total_pdf", 0)
    total_docx = resultado.get("total_docx", 0)

    if not total_pdf:
        return "⚠️ Não foi possível identificar fornecedores no PDF dos vencedores."

    if not faltantes and total_pdf == total_docx:
        return f"✅ Conferência OK: {total_pdf} fornecedor(es) no PDF e {total_docx} ata(s) gerada(s)."

    linhas = [
        "⚠️ Conferência encontrou divergência.",
        "",
        f"- Fornecedores no PDF: **{total_pdf}**",
        f"- Atas DOCX geradas: **{total_docx}**",
        f"- Fornecedores sem DOCX correspondente: **{len(faltantes)}**",
    ]

    if faltantes:
        linhas.append("")
        linhas.append("**Fornecedores faltantes:**")
        for f in faltantes:
            itens = f.get("itens") or []
            itens_txt = ", ".join(str(i) for i in itens) if itens else "-"
            valor = f.get("valor_total") or "-"
            linhas.append(f"- {f.get('nome', '')} — Itens: {itens_txt} — Total: {valor}")

    return "\n".join(linhas)
