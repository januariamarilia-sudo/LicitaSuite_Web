import re
from pathlib import Path
import pdfplumber

from licitasuite.models.fornecedor import Fornecedor, ItemFornecedor
from licitasuite.parsers.text_utils import normalize_text, parse_number

CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
SUPPLIER_MARKERS = [
    "LTDA", "S.A", "SA", "EIRELI", "COMERC", "DISTRIB", "FARMA", "HOSPITAL",
    "MEDIC", "PRODUTOS", "FARMACEUT", "SOLUCOES"
]
BAD_SUPPLIER_PREFIX = [
    "A AUTENTICIDADE", "DOCUMENTO GERADO", "CODIGO VERIFICADOR", "PAGINA ",
    "VENCEDORES DO PROCESSO", "ICISMEP", "${ICISMEP"
]
MONEY_PAIR_RE = re.compile(
    r"(?P<qtd>\d{1,3}(?:\.\d{3})*|\d+)\s+"
    r"(?P<unidade>[A-ZÇ]{2,8})\s+"
    r"R\$\s*(?P<unit>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})\s+"
    r"R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4})"
)

class PdfParseResult:
    def __init__(self, fornecedores=None, texto="", linhas=None, cnpjs=None, item_lines=None, alertas=None):
        self.fornecedores = fornecedores or []
        self.texto = texto
        self.linhas = linhas or []
        self.cnpjs = cnpjs or []
        self.item_lines = item_lines or []
        self.alertas = alertas or []

class PdfWinnersParser:
    def extract_text(self, path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError("PDF dos vencedores não localizado.")
        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(layout=True, x_tolerance=1, y_tolerance=3) or ""
                pages.append(text)
        return "\n".join(pages)

    def parse(self, path, output_text_path="output/pdf_extraido.txt"):
        text = self.extract_text(path)
        output = Path(output_text_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")

        linhas = [line.rstrip() for line in text.splitlines() if line.strip()]
        fornecedores = self._parse_suppliers(linhas)
        item_lines = [item.linha_origem for f in fornecedores for item in f.itens]
        return PdfParseResult(
            fornecedores=fornecedores,
            texto=text,
            linhas=linhas,
            cnpjs=CNPJ_RE.findall(text),
            item_lines=item_lines,
        )

    def _is_bad_supplier_line(self, line):
        n = normalize_text(line)
        return any(n.startswith(bad) for bad in BAD_SUPPLIER_PREFIX)

    def _looks_supplier_line(self, line):
        n = normalize_text(line)
        if self._is_bad_supplier_line(line):
            return False
        if not CNPJ_RE.search(line):
            return False
        return any(marker in n for marker in SUPPLIER_MARKERS) or "|" in line

    def _parse_suppliers(self, linhas):
        indices = [i for i, line in enumerate(linhas) if self._looks_supplier_line(line)]
        fornecedores = []

        for pos, start in enumerate(indices):
            end = indices[pos + 1] if pos + 1 < len(indices) else len(linhas)
            bloco = linhas[start:end]
            fornecedor = self._parse_supplier_header(bloco[0])
            if not fornecedor:
                continue
            fornecedor.itens = self._parse_items_in_block(bloco)
            if fornecedor.itens:
                fornecedores.append(fornecedor)

        return fornecedores

    def _parse_supplier_header(self, line):
        if self._is_bad_supplier_line(line):
            return None

        cnpj = CNPJ_RE.search(line)
        if not cnpj:
            return None

        before = line[:cnpj.start()].strip(" -|")
        name = before.split("| Tipo:")[0].strip()
        if not name or self._is_bad_supplier_line(name):
            return None

        tipo = ""
        m_tipo = re.search(r"\|\s*Tipo:\s*(.*?)\s*-\s*LC123", line, re.IGNORECASE)
        if m_tipo:
            tipo = m_tipo.group(1).strip()

        return Fornecedor(
            razao_social=name,
            cnpj=cnpj.group(0),
            tipo=tipo,
            endereco=self._extract_after(line, "Endereço:", "CEP:"),
            cep=self._extract_after(line, "CEP:", "UF:"),
            uf=self._extract_after(line, "UF:", "Município:"),
            municipio=self._extract_after(line, "Município:", "Telefone:"),
            telefone=self._extract_after(line, "Telefone:", None),
        )

    def _extract_after(self, text, start_label, end_label=None):
        if start_label not in text:
            return ""
        part = text.split(start_label, 1)[1]
        if end_label and end_label in part:
            part = part.split(end_label, 1)[0]
        return part.strip(" -|")

    def _parse_items_in_block(self, bloco):
        rows = []
        current = ""

        for line in bloco[1:]:
            clean = " ".join(line.split())
            n = normalize_text(clean)
            if not clean:
                continue
            if any(n.startswith(x) for x in ["CODIGO PRODUTO", "TOTAL DO VENCEDOR", "A AUTENTICIDADE", "DOCUMENTO GERADO", "PAGINA "]):
                if current:
                    rows.append(current)
                    current = ""
                continue

            if re.match(r"^\d{4}\s+", clean):
                if current:
                    rows.append(current)
                current = clean
            elif current:
                current += " " + clean

        if current:
            rows.append(current)

        itens = []
        seen = set()
        for row in rows:
            item = self._parse_item_row(row)
            if item and item.numero_item not in seen:
                itens.append(item)
                seen.add(item.numero_item)

        return itens

    def _parse_item_row(self, row):
        m = re.match(r"^(?P<codigo>\d{4})\s+(?P<body>.+)$", row)
        if not m:
            return None

        numero_item = int(m.group("codigo"))
        body = m.group("body")
        money = MONEY_PAIR_RE.search(body)
        if not money:
            return ItemFornecedor(numero_item=numero_item, linha_origem=row)

        quantidade = parse_number(money.group("qtd"))
        valor_unitario = parse_number(money.group("unit"))
        valor_total = parse_number(money.group("total"))

        before_qtd = body[:money.start()].strip()
        marca = self._guess_brand_model(before_qtd)

        return ItemFornecedor(
            numero_item=numero_item,
            marca=marca,
            fabricante="",
            modelo="",
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            valor_total=valor_total,
            linha_origem=row,
        )

    def _guess_brand_model(self, text):
        text = re.sub(r"\([^)]*CONFORME EDITAL[^)]*\)", "", text, flags=re.IGNORECASE)
        words = text.split()
        if len(words) <= 2:
            return text
        # pega um trecho final como marca/modelo; descrição oficial virá do apêndice.
        return " ".join(words[-4:])
