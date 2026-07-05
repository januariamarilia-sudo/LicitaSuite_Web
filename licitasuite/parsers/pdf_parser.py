import re
from pathlib import Path
import pdfplumber
from licitasuite.models.fornecedor import Fornecedor, ItemFornecedor
from licitasuite.parsers.text_utils import normalize_text, parse_number
from licitasuite.core.exceptions import PdfParserError

CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
MONEY_RE = re.compile(r"(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2,4}|(?:R\$\s*)?\d+,\d{2,4}")

class PdfParseResult:
    def __init__(self, fornecedores=None, texto="", linhas=None, cnpjs=None, item_lines=None):
        self.fornecedores = fornecedores or []
        self.texto = texto
        self.linhas = linhas or []
        self.cnpjs = cnpjs or []
        self.item_lines = item_lines or []

class PdfWinnersParser:
    def extract_text(self, path):
        path = Path(path)
        if not path.exists():
            raise PdfParserError("PDF dos vencedores não localizado.")

        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text(layout=True, x_tolerance=1, y_tolerance=3) or "")
        return "\\n".join(pages)

    def parse(self, path, output_text_path="output/pdf_extraido.txt"):
        text = self.extract_text(path)
        output = Path(output_text_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")

        linhas = [line.rstrip() for line in text.splitlines() if line.strip()]
        cnpjs = CNPJ_RE.findall(text)
        fornecedores = self._parse_blocks(linhas)
        item_lines = [item.linha_origem for f in fornecedores for item in f.itens]
        return PdfParseResult(fornecedores=fornecedores, texto=text, linhas=linhas, cnpjs=cnpjs, item_lines=item_lines)

    def _parse_blocks(self, linhas):
        indices = [idx for idx, line in enumerate(linhas) if CNPJ_RE.search(line)]
        fornecedores = []

        for pos, idx in enumerate(indices):
            end = indices[pos + 1] if pos + 1 < len(indices) else len(linhas)
            start = max(0, idx - 3)
            bloco = linhas[start:end]
            texto = "\\n".join(bloco)
            cnpj_match = CNPJ_RE.search(texto)
            if not cnpj_match:
                continue

            fornecedor = Fornecedor(
                razao_social=self._guess_supplier_name(bloco, cnpj_match.group(0)),
                cnpj=cnpj_match.group(0)
            )

            seen = set()
            for line in bloco:
                item = self._parse_item_line(line)
                if item and item.numero_item not in seen:
                    fornecedor.itens.append(item)
                    seen.add(item.numero_item)

            fornecedores.append(fornecedor)

        return fornecedores

    def _guess_supplier_name(self, bloco, cnpj):
        for line in bloco:
            if cnpj in line:
                before = line.split(cnpj)[0].strip(" -:|")
                if len(before) >= 3:
                    return before
        for line in bloco:
            n = normalize_text(line)
            if any(x in n for x in ["LTDA", "EIRELI", "COMERCIO", "DISTRIBUIDORA", "ME", "EPP", "INSTRUMENTOS", "AUTOMEDICAL", "CENTRAL"]):
                cleaned = CNPJ_RE.sub("", line).strip(" -:|")
                if len(cleaned) >= 3:
                    return cleaned
        return "FORNECEDOR NÃO IDENTIFICADO"

    def _parse_item_line(self, line):
        clean = " ".join(line.split())
        item_match = re.match(r"^\s*(?:ITEM\s*)?(\d{1,4})\b", clean, flags=re.IGNORECASE)
        if not item_match:
            return None

        numero_item = int(item_match.group(1))
        money_values = MONEY_RE.findall(clean)

        valor_unitario = parse_number(money_values[-2]) if len(money_values) >= 2 else 0.0
        valor_total = parse_number(money_values[-1]) if money_values else 0.0
        quantidade = self._guess_quantity(clean, item_match.end(), money_values[0] if money_values else "")
        marca, fabricante, modelo = self._guess_text_fields(clean, item_match.end(), money_values[0] if money_values else "")

        return ItemFornecedor(numero_item, marca, fabricante, modelo, quantidade, valor_unitario, valor_total, clean)

    def _guess_quantity(self, line, start_pos, first_money):
        before_money = line.split(first_money)[0] if first_money and first_money in line else line
        candidates = re.findall(r"\\b\\d{1,6}(?:[.,]\\d+)?\\b", before_money[start_pos:])
        return parse_number(candidates[-1]) if candidates else 0.0

    def _guess_text_fields(self, line, start_pos, first_money):
        before_money = line.split(first_money)[0] if first_money and first_money in line else line
        text = before_money[start_pos:].strip()
        text = re.sub(r"\\b\\d{1,6}(?:[.,]\\d+)?\\b\\s*$", "", text).strip(" -|")
        return text, "", ""
