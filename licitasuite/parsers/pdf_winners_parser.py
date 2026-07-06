import re
from pathlib import Path
import pdfplumber

from licitasuite.models.fornecedor import Fornecedor, ItemFornecedor
from licitasuite.parsers.text_utils import normalize_text, parse_number

CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}")
LOTE_LINE_RE = re.compile(r"^(?P<lote>\d{4})\s+Lote\s*0*(?P<lotenum>\d+)", re.I)
ITEM_LINE_RE = re.compile(r"^(?P<item>\d{4})\s+(?P<body>.+)")
MONEY_RE = re.compile(
    r"(?P<qtd>\d{1,3}(?:\.\d{3})*|\d+)\s*"
    r"(?P<un>UND|CX|UN|PC|PCT|M|MT|RL|ROLO|KIT)?\s+"
    r"R\$\s*(?P<unit>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})\s+"
    r"R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})"
)

BAD_PREFIXES = [
    "A AUTENTICIDADE", "DOCUMENTO GERADO", "CODIGO VERIFICADOR", "PAGINA ",
    "VENCEDORES DO PROCESSO", "ICISMEP", "${ICISMEP", "REGISTRO DE PRECOS",
    "LOTE ITEM PRODUTO"
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

        # Em alguns PDFs, fornecedor vem colado sem espaços. Normaliza quebras antes de CNPJ e fornecedor.
        lines = [self._clean_line(ln) for ln in text.splitlines() if ln.strip()]
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

    def _clean_line(self, line):
        return line.replace("L.DESOUSA", "L. DE SOUSA").replace("LTDA-Tipo", "LTDA - Tipo").strip()

    def _is_noise(self, line):
        n = normalize_text(line)
        return any(n.startswith(p) for p in BAD_PREFIXES)

    def _is_supplier_line(self, line):
        if self._is_noise(line):
            return False
        if not CNPJ_RE.search(line):
            return False
        n = normalize_text(line)
        supplier_words = ["LTDA", "EIRELI", "S.A", " SA ", "COMERC", "DISTRIB", "FARMA", "HOSPITAL", "MEDIC", "PRODUTOS", "SERVICOS", "SEGURANCA"]
        return any(w in n for w in supplier_words) or "TIPO:" in n

    def _parse_supplier(self, line):
        cnpj_match = CNPJ_RE.search(line)
        cnpj = cnpj_match.group(0) if cnpj_match else ""
        before_cnpj = line[:cnpj_match.start()] if cnpj_match else line
        name = before_cnpj.split("| Tipo:")[0].split("- Tipo:")[0].strip(" -|")
        if not name:
            # Sometimes CNPJ is before continuation
            name = line.split("- Tipo:", 1)[0].strip(" -|")
        tipo = self._between(line, "Tipo:", "- LC123")
        return Fornecedor(
            razao_social=name,
            cnpj=cnpj,
            tipo=tipo,
            endereco=self._between(line, "Endereço:", "CEP:") or self._between(line, "Endereço:", "-CEP:"),
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
        current_lote = None
        for line in lines:
            n = normalize_text(line)
            if n.startswith("TOTAL DO VENCEDOR") or n.startswith("TOTALDO VENCEDOR"):
                if current:
                    rows.append((current_lote, current))
                    current = ""
                continue

            lm = LOTE_LINE_RE.match(line)
            if lm:
                if current:
                    rows.append((current_lote, current))
                    current = ""
                current_lote = int(lm.group("lotenum"))
                continue

            if ITEM_LINE_RE.match(line):
                if current:
                    rows.append((current_lote, current))
                current = line
            elif current:
                current += " " + line

        if current:
            rows.append((current_lote, current))

        items = []
        seen = set()
        for lote, row in rows:
            item = self._parse_item(row, lote)
            if item:
                key = (item.lote, item.item_display or item.numero_item)
                if key not in seen:
                    items.append(item)
                    seen.add(key)
        return items

    def _parse_item(self, row, lote):
        m = ITEM_LINE_RE.match(row)
        if not m:
            return None
        item_num = int(m.group("item"))
        body = m.group("body")
        money = MONEY_RE.search(body)
        if not money:
            unique = (lote or 0) * 10000 + item_num if lote else item_num
            return ItemFornecedor(numero_item=unique, linha_origem=row, lote=lote, item_display=str(item_num))

        qtd = parse_number(money.group("qtd"))
        unit = parse_number(money.group("unit"))
        total = parse_number(money.group("total"))
        before = body[:money.start()].strip()
        marca, modelo = self._guess_brand_model(before)
        unique = (lote or 0) * 10000 + item_num if lote else item_num

        return ItemFornecedor(
            numero_item=unique,
            marca=marca,
            modelo=modelo,
            quantidade_pdf=qtd,
            valor_unitario=unit,
            valor_total=total,
            linha_origem=row,
            lote=lote,
            item_display=str(item_num),
        )

    def _guess_brand_model(self, text):
        parts = text.split()
        if len(parts) >= 2:
            # tentativa simples: últimas duas expressões antes da quantidade como modelo/marca
            return parts[-1], parts[-2]
        return text, ""
