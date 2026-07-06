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

TOTAL_RE = re.compile(
    r"TOTAL\s+DO\s+VENCEDOR\s+R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})",
    flags=re.I,
)

SUPPLIER_RE = re.compile(
    r"(?P<name>.+?)\s*\|\s*Tipo:\s*(?P<tipo>.*?)-\s*LC123:.*?Documento\s+(?P<cnpj>\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
    flags=re.I,
)

HEADER_RE = re.compile(r"(?m)^(.+?)\s+\|\s*Tipo:", flags=re.I)

BAD_PREFIXES = [
    "A AUTENTICIDADE",
    "DOCUMENTO GERADO",
    "CODIGO VERIFICADOR",
    "PAGINA ",
    "VENCEDORES DO PROCESSO",
    "ICISMEP",
    "${ICISMEP",
    "REGISTRO DE PRECOS",
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

        suppliers = self._parse_by_supplier_blocks(text)

        # Fallback: mantém a lógica antiga se por algum motivo o bloco robusto falhar.
        if not suppliers:
            suppliers = self._parse_legacy_lines(text)

        return suppliers

    # ---------------------------------------------------------------------
    # NOVO PARSER ROBUSTO
    # ---------------------------------------------------------------------

    def _parse_by_supplier_blocks(self, text):
        text = self._prepare_text(text)
        headers = list(HEADER_RE.finditer(text))

        suppliers = []

        for idx, header in enumerate(headers):
            start = header.start()
            end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
            block = text[start:end].strip()

            fornecedor = self._parse_supplier_block(block)
            if not fornecedor:
                continue

            fornecedor.itens = self._parse_item_rows_from_block(block)

            # Importante: mesmo fornecedor com um item cujo valor não foi capturado
            # deve entrar, para não sumir ata inteira.
            if fornecedor.itens:
                suppliers.append(fornecedor)

        return suppliers

    def _prepare_text(self, text):
        text = text or ""
        text = text.replace("\xa0", " ")
        text = text.replace("\u00ad", "")
        text = text.replace("OTO\ufffeBETNOVATE", "OTO-BETNOVATE")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _parse_supplier_block(self, block):
        first_part = block[:1200]
        m = SUPPLIER_RE.search(first_part)

        if not m:
            return None

        line = " ".join(block.splitlines()[:6])
        line = " ".join(line.split())

        name = re.sub(r"\s+", " ", m.group("name")).strip(" -|")
        tipo = re.sub(r"\s+", " ", m.group("tipo")).strip(" -|")
        cnpj = m.group("cnpj")

        return Fornecedor(
            razao_social=name,
            cnpj=cnpj,
            tipo=tipo,
            endereco=self._between(line, "Endereço:", "CEP:"),
            cep=self._between(line, "CEP:", "UF:"),
            uf=self._between(line, "UF:", "Município:"),
            municipio=self._between(line, "Município:", "Telefone:"),
            telefone=self._after(line, "Telefone:"),
        )

    def _parse_item_rows_from_block(self, block):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        lines = [ln for ln in lines if not self._is_noise(" ".join(ln.split()))]

        rows = []
        current = ""

        for line in lines:
            clean = " ".join(line.split())

            if self._is_supplier_line(clean):
                continue

            if normalize_text(clean).startswith("CODIGO PRODUTO"):
                continue

            if normalize_text(clean).startswith("TOTAL DO VENCEDOR"):
                if current:
                    rows.append(current)
                    current = ""
                continue

            if ITEM_START_RE.match(clean):
                if current:
                    rows.append(current)
                current = clean
            elif current:
                current += " " + clean

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

    # ---------------------------------------------------------------------
    # PARSER ANTIGO COMO FALLBACK
    # ---------------------------------------------------------------------

    def _parse_legacy_lines(self, text):
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
        return any(n.startswith(p) for p in BAD_PREFIXES) or n in {
            "CODIGO PRODUTO MODELO MARCA/FABRICANTE QTDE VALOR UNITARIO VALOR TOTAL"
        }

    def _is_supplier_line(self, line):
        if self._is_noise(line):
            return False

        if "| Tipo:" not in line and "| TIPO:" not in normalize_text(line):
            return False

        if not CNPJ_RE.search(line):
            # No PDF, algumas linhas longas podem quebrar antes do CNPJ.
            # Para o parser novo isso não impede, mas para o legado sim.
            return False

        return True

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
            telefone=self._after(line, "Telefone:"),
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

        if money:
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
                linha_origem=row,
            )

        # Fallback para itens em que o PDF quebrou entre "R$" e o valor total.
        # Exemplo:
        # ... CPR R$ 0,9000 R$ 2.107.006,2000
        money_values = re.findall(r"R\$\s*([0-9\.\,]+)", body)
        qtd_un = re.search(r"(\d{1,3}(?:\.\d{3})*|\d+)\s+([A-ZÇ]{2,8})\s+R\$", body)

        if money_values and qtd_un:
            qtd = parse_number(qtd_un.group(1))
            unit = parse_number(money_values[-2]) if len(money_values) >= 2 else 0
            total = parse_number(money_values[-1])
            before = body[:qtd_un.start()].strip()
            marca = self._guess_brand(before)

            return ItemFornecedor(
                numero_item=numero,
                marca=marca,
                quantidade_pdf=qtd,
                valor_unitario=unit,
                valor_total=total,
                linha_origem=row,
            )

        # Último fallback: não deixa o fornecedor sumir se o item existe.
        # O item será levado adiante com valor 0 e linha_origem para conferência.
        return ItemFornecedor(
            numero_item=numero,
            marca=self._guess_brand(body),
            quantidade_pdf=0,
            valor_unitario=0,
            valor_total=0,
            linha_origem=row,
        )

    def _guess_brand(self, text):
        text = re.sub(r"\([^)]*CONFORME EDITAL[^)]*\)", "", text, flags=re.I)
        parts = text.split()

        if len(parts) <= 4:
            return " ".join(parts)

        return " ".join(parts[-4:])
