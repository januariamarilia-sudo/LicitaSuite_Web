import re
from pathlib import Path

import pdfplumber

from licitasuite.models.fornecedor import Fornecedor, ItemFornecedor
from licitasuite.parsers.text_utils import normalize_text, parse_number


CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\s*\d{2}")
SUPPLIER_HEADER_RE = re.compile(r"(?m)^(.+?)\s+\|\s*Tipo:", flags=re.I)
ITEM_START_RE = re.compile(r"^(?P<codigo>\d{4})\s+(?P<body>.+)")
TABLE_HEADER_RE = re.compile(
    r"C[oó]digo\s+Produto\s+Modelo\s+Marca/Fabricante\s+Qtde\s+Valor\s+Unit[aá]rio\s+Valor\s+Total",
    flags=re.I,
)
TOTAL_VENCEDOR_RE = re.compile(
    r"TOTAL\s+DO\s+VENCEDOR\s+R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})",
    flags=re.I,
)

MONEY_PAIR_RE = re.compile(
    r"(?P<qtd>\d{1,3}(?:\.\d{3})*|\d+)\s+"
    r"(?P<un>[A-ZÇ]{2,8})\s+"
    r"R\$\s*(?P<unit>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})\s+"
    r"R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})",
    flags=re.I,
)

QTD_UN_RE = re.compile(
    r"(?P<qtd>\d{1,3}(?:\.\d{3})*|\d+)\s+(?P<un>[A-ZÇ]{2,8})\s+R\$",
    flags=re.I,
)

MONEY_VALUE_RE = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})")


class PdfWinnersParser:
    """
    Parser LTS para PDF de Vencedores do Processo.

    Regras:
    - identifica fornecedores por bloco;
    - só lê itens após o cabeçalho da tabela;
    - para no TOTAL DO VENCEDOR;
    - aceita CNPJ quebrado;
    - não captura telefone/CEP como item;
    - usa TOTAL DO VENCEDOR como validação oficial;
    - se o fornecedor tiver item único, usa o total oficial como valor do item;
    - se valor não for lido, mantém 0 e marca linha_origem para conferência.
    """

    def extract_text(self, path):
        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(layout=True, x_tolerance=1, y_tolerance=3) or ""
                pages.append(text)
        return "\n".join(pages)

    def parse(self, path):
        text = self.extract_text(path)

        out = Path("output/pdf_extraido_layout.txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")

        text = self._prepare_text(text)
        blocks = self._split_supplier_blocks(text)

        suppliers = []

        for block in blocks:
            fornecedor = self._parse_supplier(block)
            if not fornecedor:
                continue

            fornecedor_total = self._parse_total_vencedor(block)
            fornecedor.itens = self._parse_items_only_inside_table(block)

            self._apply_total_validation(fornecedor, fornecedor_total)

            if fornecedor.itens:
                suppliers.append(fornecedor)

        return suppliers

    def _prepare_text(self, text):
        text = text or ""
        text = text.replace("\xa0", " ")
        text = text.replace("\u00ad", "")
        text = text.replace("\ufffe", "-")
        text = text.replace("OTO-BETNOVATE", "OTO BETNOVATE")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _split_supplier_blocks(self, text):
        headers = list(SUPPLIER_HEADER_RE.finditer(text))
        blocks = []

        for i, header in enumerate(headers):
            start = header.start()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            block = text[start:end].strip()
            if block:
                blocks.append(block)

        return blocks

    def _parse_supplier(self, block):
        first = block[:2200]

        cnpj_match = CNPJ_RE.search(first)
        if not cnpj_match:
            return None

        cnpj = re.sub(r"\s+", "", cnpj_match.group(0))

        name_match = re.search(r"^(.+?)\s+\|\s*Tipo:", first, flags=re.I | re.M)
        if not name_match:
            return None

        name = self._clean_spaces(name_match.group(1)).strip(" -|")

        tipo = self._between(first, "| Tipo:", "- LC123")
        endereco = self._between(first, "Endereço:", "CEP:")
        cep = self._between(first, "CEP:", "UF:")
        uf = self._between(first, "UF:", "Município:")
        municipio = self._between(first, "Município:", "Telefone:")
        telefone = self._after(first, "Telefone:")
        telefone = re.split(r"C[oó]digo\s+Produto", telefone, flags=re.I)[0].strip(" -|")

        return Fornecedor(
            razao_social=name,
            cnpj=cnpj,
            tipo=tipo,
            endereco=endereco,
            cep=cep,
            uf=uf,
            municipio=municipio,
            telefone=telefone,
        )

    def _parse_total_vencedor(self, block):
        m = TOTAL_VENCEDOR_RE.search(block)
        if not m:
            return 0
        return parse_number(m.group("total"))

    def _table_region(self, block):
        header = TABLE_HEADER_RE.search(block)
        if not header:
            return ""

        start = header.end()
        total = re.search(r"TOTAL\s+DO\s+VENCEDOR", block[start:], flags=re.I)
        end = start + total.start() if total else len(block)

        return block[start:end].strip()

    def _parse_items_only_inside_table(self, block):
        table = self._table_region(block)
        if not table:
            return []

        lines = [self._clean_spaces(ln) for ln in table.splitlines() if ln.strip()]
        rows = []
        current = ""

        for line in lines:
            n = normalize_text(line)

            if n.startswith("TOTAL DO VENCEDOR"):
                break

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
        body = self._clean_spaces(m.group("body"))

        money = MONEY_PAIR_RE.search(body)
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

        qtd_un = QTD_UN_RE.search(body)
        valores = MONEY_VALUE_RE.findall(body)

        if qtd_un and valores:
            qtd = parse_number(qtd_un.group("qtd"))
            unit = parse_number(valores[-2]) if len(valores) >= 2 else 0
            total = parse_number(valores[-1]) if len(valores) >= 1 else 0
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

        return ItemFornecedor(
            numero_item=numero,
            marca=self._guess_brand(body),
            quantidade_pdf=0,
            valor_unitario=0,
            valor_total=0,
            linha_origem="VALOR_TOTAL_NAO_DETECTADO_MANUALMENTE | " + row,
        )

    def _apply_total_validation(self, fornecedor, fornecedor_total):
        if not fornecedor.itens or not fornecedor_total:
            return

        if len(fornecedor.itens) == 1:
            item = fornecedor.itens[0]
            if not item.valor_total or abs(float(item.valor_total) - float(fornecedor_total)) > 0.01:
                item.valor_total = fornecedor_total
                if item.quantidade_pdf:
                    try:
                        item.valor_unitario = fornecedor_total / item.quantidade_pdf
                    except Exception:
                        pass
                item.linha_origem = str(item.linha_origem) + " | TOTAL_OFICIAL_DO_VENCEDOR_APLICADO"
            return

        soma = sum(float(getattr(item, "valor_total", 0) or 0) for item in fornecedor.itens)

        if abs(soma - float(fornecedor_total)) > 0.05:
            for item in fornecedor.itens:
                item.linha_origem = (
                    str(item.linha_origem)
                    + f" | ATENCAO_SOMA_ITENS_DIVERGE_TOTAL_VENCOR={fornecedor_total}"
                )

    def _guess_brand(self, text):
        text = re.sub(r"\([^)]*CONFORME EDITAL[^)]*\)", "", text, flags=re.I)
        parts = text.split()

        if len(parts) <= 4:
            return " ".join(parts)

        return " ".join(parts[-4:])

    def _between(self, text, a, b):
        if a not in text:
            return ""

        part = text.split(a, 1)[1]

        if b and b in part:
            part = part.split(b, 1)[0]

        return self._clean_spaces(part).strip(" -|")

    def _after(self, text, a):
        if a not in text:
            return ""

        return self._clean_spaces(text.split(a, 1)[1]).strip(" -|")

    def _clean_spaces(self, value):
        return re.sub(r"\s+", " ", value or "").strip()
