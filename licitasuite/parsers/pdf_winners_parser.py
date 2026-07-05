import re
from pathlib import Path
import pdfplumber

from licitasuite.models.fornecedor import Fornecedor, ItemFornecedor
from licitasuite.parsers.text_utils import normalize_text, parse_number

CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
ITEM_START_RE = re.compile(r"^(?P<codigo>\d{4})\s+(?P<body>.+)")
MONEY_RE = re.compile(
    r"(?P<qtd>\d{1,3}(?:\.\d{3})*|\d+)\s+"
    r"(?P<un>[A-ZÇ]{2,8})\s+"
    r"R\$\s*(?P<unit>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})\s+"
    r"R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})"
)

BAD_PREFIXES = [
    "A AUTENTICIDADE", "DOCUMENTO GERADO", "CODIGO VERIFICADOR", "PAGINA ",
    "VENCEDORES DO PROCESSO", "ICISMEP", "${ICISMEP", "REGISTRO DE PRECOS"
]

class PdfWinnersParser:
    def extract_text(self, path):
        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text(layout=True, x_tolerance=1, y_tolerance=3) or "")
        return "\n".join(pages)

    def parse(self, path):
        text = self.extract_text(path)
        out = Path("output/pdf_extraido_layout.txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")

        lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
        suppliers = []
        current = None
        buffer_items = []

        for line in lines:
            clean = " ".join(line.split())
            if self._is_noise(clean):
                continue

            if self._is_supplier_line(clean):
                if current:
                    current.itens = self._parse_item_rows(buffer_items)
                    if current.itens:
                        suppliers.append(current)
                current = self._parse_supplier(clean)
                buffer_items = []
                continue

            if current:
                buffer_items.append(clean)

        if current:
            current.itens = self._parse_item_rows(buffer_items)
            if current.itens:
                suppliers.append(current)

        return suppliers

    def _is_noise(self, line):
        n = normalize_text(line)
        return any(n.startswith(p) for p in BAD_PREFIXES) or n in {"CODIGO PRODUTO MODELO MARCA/FABRICANTE QTDE VALOR UNITARIO VALOR TOTAL"}

    def _is_supplier_line(self, line):
        if self._is_noise(line):
            return False
        if not CNPJ_RE.search(line):
            return False
        n = normalize_text(line)
        supplier_words = ["LTDA", "EIRELI", "S.A", " SA ", "COMERC", "DISTRIB", "FARMA", "HOSPITAL", "MEDIC", "PRODUTOS"]
        return any(w in n for w in supplier_words) or "| TIPO:" in n

    def _parse_supplier(self, line):
        cnpj = CNPJ_RE.search(line).group(0)
        before_cnpj = line.split(cnpj, 1)[0]
        name = before_cnpj.split("| Tipo:")[0].strip(" -|")
        tipo = self._between(line, "| Tipo:", "- LC123")
        return Fornecedor(
            razao_social=name,
            cnpj=cnpj,
            tipo=tipo,
            endereco=self._between(line, "Endereço:", "CEP:"),
            cep=self._between(line, "CEP:", "UF:"),
            uf=self._between(line, "UF:", "Município:"),
            municipio=self._between(line, "Município:", "Telefone:"),
            telefone=self._after(line, "Telefone:")
        )

    def _between(self, text, a, b):
        if a not in text:
            return ""
        part = text.split(a, 1)[1]
        if b and b in part:
            part = part.split(b, 1)[0]
        return part.strip(" -|")

    def _after(self, text, a):
        if a not in text:
            return ""
        return text.split(a, 1)[1].strip(" -|")

    def _parse_item_rows(self, lines):
        rows = []
        current = ""
        for line in lines:
            n = normalize_text(line)
            if n.startswith("TOTAL DO VENCEDOR"):
                if current:
                    rows.append(current)
                    current = ""
                continue
            if ITEM_START_RE.match(line):
                if current:
                    rows.append(current)
                current = line
            elif current:
                current += " " + line
        if current:
            rows.append(current)

        items = []
        seen = set()
        for row in rows:
            item = self._parse_item(row)
            if item and item.numero_item not in seen:
                items.append(item)
                seen.add(item.numero_item)
        return items

    def _parse_item(self, row):
        m = ITEM_START_RE.match(row)
        if not m:
            return None
        numero = int(m.group("codigo"))
        body = m.group("body")
        money = MONEY_RE.search(body)
        if not money:
            return ItemFornecedor(numero_item=numero, linha_origem=row)

        qtd = parse_number(money.group("qtd"))
        unit = parse_number(money.group("unit"))
        total = parse_number(money.group("total"))

        before = body[:money.start()].strip()
        marca = self._guess_brand(before)

        return ItemFornecedor(
            numero_item=numero,
            marca=marca,
            quantidade_pdf=qtd,
            valor_unitario=unit,
            valor_total=total,
            linha_origem=row
        )

    def _guess_brand(self, text):
        text = re.sub(r"\([^)]*CONFORME EDITAL[^)]*\)", "", text, flags=re.I)
        parts = text.split()
        if len(parts) <= 4:
            return " ".join(parts)
        return " ".join(parts[-4:])
