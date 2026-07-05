import re
from licitasuite.parsers.text_utils import parse_number

MONEY_RE = re.compile(r"(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2,4}|(?:R\$\s*)?\d+,\d{2,4}")

class PdfFieldExtractor:
    """
    Extrator auxiliar para linhas de item do PDF.

    Centraliza a interpretação dos campos variáveis para que
    o parser principal fique mais fácil de ajustar por processo.
    """

    def extract_item_fields(self, line: str) -> dict:
        clean = " ".join((line or "").split())

        item = self._extract_item(clean)
        money_values = MONEY_RE.findall(clean)

        valor_unitario = parse_number(money_values[-2]) if len(money_values) >= 2 else 0.0
        valor_total = parse_number(money_values[-1]) if money_values else 0.0

        quantidade = self._extract_quantity(clean, money_values[0] if money_values else "")
        text_part = self._text_before_values(clean, money_values[0] if money_values else "")
        marca, fabricante, modelo = self._split_product_fields(text_part)

        return {
            "item": item,
            "marca": marca,
            "fabricante": fabricante,
            "modelo": modelo,
            "quantidade": quantidade,
            "valor_unitario": valor_unitario,
            "valor_total": valor_total,
            "linha_origem": clean,
        }

    def _extract_item(self, line):
        match = re.match(r"^\s*(?:ITEM\s*)?(\d{1,4})\b", line, flags=re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _extract_quantity(self, line, first_money):
        before_money = line.split(first_money)[0] if first_money and first_money in line else line
        candidates = re.findall(r"\b\d{1,6}(?:[.,]\d+)?\b", before_money)
        if len(candidates) <= 1:
            return 0.0
        return parse_number(candidates[-1])

    def _text_before_values(self, line, first_money):
        if first_money and first_money in line:
            line = line.split(first_money)[0]
        line = re.sub(r"^\s*(?:ITEM\s*)?\d{1,4}\b", "", line, flags=re.IGNORECASE).strip()
        line = re.sub(r"\b\d{1,6}(?:[.,]\d+)?\b\s*$", "", line).strip(" -|")
        return line

    def _split_product_fields(self, text):
        if not text:
            return "", "", ""

        for sep in [" | ", " / ", " - ", ";"]:
            if sep in text:
                parts = [p.strip() for p in text.split(sep) if p.strip()]
                if len(parts) >= 3:
                    return parts[0], parts[1], " ".join(parts[2:])
                if len(parts) == 2:
                    return parts[0], parts[1], ""

        return text, "", ""
