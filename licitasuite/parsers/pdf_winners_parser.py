import re
from pathlib import Path

import pdfplumber

from licitasuite.models.fornecedor import Fornecedor, ItemFornecedor
from licitasuite.parsers.text_utils import normalize_text, parse_number


CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\s*\d{2}")
SUPPLIER_HEADER_RE = re.compile(r"(?m)^\s*(.+?)\s*(?:\|\s*Tipo:|\s+-\s*Tipo:)", flags=re.I)
ITEM_START_RE = re.compile(r"^(?P<codigo>\d{4})\s+(?P<body>.+)")

TOTAL_OFICIAL_RE = re.compile(
    r"(?:TOTAL\s+DO\s+VENCEDOR|Total)\s+R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})",
    flags=re.I,
)

MONEY_PAIR_RE = re.compile(
    r"(?P<qtd>\d{1,3}(?:\.\d{3})*|\d+)\s*"
    r"(?P<un>[A-ZÇ]{2,8})?\s+"
    r"R\$\s*(?P<unit>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})\s+"
    r"R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})",
    flags=re.I,
)

QTD_UN_RE = re.compile(
    r"(?P<qtd>\d{1,3}(?:\.\d{3})*|\d+)\s*(?P<un>[A-ZÇ]{2,8})?\s+R\$",
    flags=re.I,
)

MONEY_VALUE_RE = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})")
ANY_MONEY_RE = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})(?!\d)")


class PdfWinnersParser:
    """
    Parser universal do LicitaSuite.

    Aceita:
    1. PDF "Vencedores do Processo"
       - fornecedor com "| Tipo:"
       - total com "TOTAL DO VENCEDOR R$"

    2. PDF "Relatório de Itens Vencidos pelo Fornecedor"
       - fornecedor com "- Tipo:"
       - total com "Total R$"

    Regra crítica:
    - item só é lido dentro da tabela, depois de "Código Produto ... Valor Total";
    - telefone, CEP e endereço não podem virar item;
    - total oficial do bloco é usado para validar, mas não é inventado em itens múltiplos.
    """

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

        text = self._prepare_text(text)
        blocks = self._split_supplier_blocks(text)

        suppliers = []

        for block in blocks:
            fornecedor = self._parse_supplier(block)
            if not fornecedor:
                continue

            total_oficial = self._parse_total_oficial(block)
            fornecedor.itens = self._parse_items_from_table(block)
            self._apply_total_validation(fornecedor, total_oficial)

            if fornecedor.itens:
                suppliers.append(fornecedor)

        return suppliers

    def _prepare_text(self, text):
        text = text or ""
        text = text.replace("\xa0", " ")
        text = text.replace("\u00ad", "")
        text = text.replace("\ufffe", "-")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _split_supplier_blocks(self, text):
        matches = []
        for m in SUPPLIER_HEADER_RE.finditer(text):
            header_line = m.group(0)
            name = m.group(1).strip()

            # Ignora cabeçalhos/títulos que podem conter "Tipo" sem ser fornecedor.
            n = normalize_text(name)
            if not name or n.startswith("CODIGO") or n.startswith("PAGINA") or n.startswith("DOCUMENTO"):
                continue

            # Aceita o candidato se houver CNPJ próximo depois do cabeçalho.
            window = text[m.start():m.start() + 1800]
            if CNPJ_RE.search(window):
                matches.append(m)

        blocks = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[start:end].strip()
            if block:
                blocks.append(block)

        return blocks

    def _parse_supplier(self, block):
        first = block[:2200]

        cnpj_m = CNPJ_RE.search(first)
        if not cnpj_m:
            return None
        cnpj = re.sub(r"\s+", "", cnpj_m.group(0))

        name_m = SUPPLIER_HEADER_RE.search(first)
        if not name_m:
            return None

        name = self._clean_spaces(name_m.group(1)).strip(" -|")

        if "| Tipo:" in first:
            tipo = self._between(first, "| Tipo:", "- LC123")
        else:
            tipo = self._between(first, "- Tipo:", "- LC123")

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

    def _parse_total_oficial(self, block):
        values = [parse_number(m.group("total")) for m in TOTAL_OFICIAL_RE.finditer(block)]
        return values[-1] if values else 0

    def _table_region(self, block):
        header = re.search(r"C[oó]digo\s+Produto.*?Valor\s+Total", block, flags=re.I | re.S)
        if not header:
            return ""

        start = header.end()

        stop_candidates = []

        m1 = re.search(r"TOTAL\s+DO\s+VENCEDOR", block[start:], flags=re.I)
        if m1:
            stop_candidates.append(start + m1.start())

        m2 = re.search(r"(?m)^\s*Total\s+R\$", block[start:], flags=re.I)
        if m2:
            stop_candidates.append(start + m2.start())

        end = min(stop_candidates) if stop_candidates else len(block)
        return block[start:end].strip()

    def _parse_items_from_table(self, block):
        table = self._table_region(block)
        if not table:
            return []

        lines = [self._clean_spaces(ln) for ln in table.splitlines() if ln.strip()]
        rows = []
        current = ""

        for line in lines:
            n = normalize_text(line)

            if n.startswith("TOTAL DO VENCEDOR") or n.startswith("TOTAL R$"):
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

        # Caminho principal: quantidade/unidade + valor unitario + valor total.
        money = MONEY_PAIR_RE.search(body)
        if money:
            before = body[:money.start()].strip()
            return ItemFornecedor(
                numero_item=numero,
                marca=self._guess_brand(before),
                quantidade_pdf=parse_number(money.group("qtd")),
                valor_unitario=parse_number(money.group("unit")),
                valor_total=parse_number(money.group("total")),
                linha_origem=row,
            )

        # Caminho preferencial: quantidade/unidade antes de R$.
        qtd_un = QTD_UN_RE.search(body)

        if qtd_un:
            qtd = parse_number(qtd_un.group("qtd"))
            before = body[:qtd_un.start()].strip()
            marca = self._guess_brand(before)

            after_qtd = body[qtd_un.end():]

            unit_m = MONEY_VALUE_RE.search(after_qtd)
            if unit_m:
                unit_text = unit_m.group(1)
                unit = parse_number(unit_text)
                after_unit = after_qtd[unit_m.end():]

                total_m = MONEY_VALUE_RE.search(after_unit)
                total_text = ""

                if total_m:
                    total_text = total_m.group(1)
                else:
                    nums = ANY_MONEY_RE.findall(after_unit)
                    nums = [n for n in nums if n != unit_text]
                    if nums:
                        total_text = nums[-1]

                if total_text:
                    return ItemFornecedor(
                        numero_item=numero,
                        marca=marca,
                        quantidade_pdf=qtd,
                        valor_unitario=unit,
                        valor_total=parse_number(total_text),
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

    def _apply_total_validation(self, fornecedor, total_oficial):
        if not fornecedor.itens or not total_oficial:
            return

        if len(fornecedor.itens) == 1:
            item = fornecedor.itens[0]
            if abs(float(item.valor_total or 0) - float(total_oficial)) > 0.05:
                item.valor_total = total_oficial
                if item.quantidade_pdf:
                    try:
                        item.valor_unitario = total_oficial / item.quantidade_pdf
                    except Exception:
                        pass
                item.linha_origem = str(item.linha_origem) + " | TOTAL_OFICIAL_DO_VENCEDOR_APLICADO"
            return

        soma = sum(float(getattr(item, "valor_total", 0) or 0) for item in fornecedor.itens)

        # Não corrige automaticamente em múltiplos itens: marca para conferência.
        if abs(soma - float(total_oficial)) > 0.05:
            for item in fornecedor.itens:
                item.linha_origem = (
                    str(item.linha_origem)
                    + f" | ATENCAO_SOMA_ITENS_DIVERGE_TOTAL_VENCEDOR={total_oficial}"
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
