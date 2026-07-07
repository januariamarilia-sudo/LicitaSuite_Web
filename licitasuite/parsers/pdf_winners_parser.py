import json
import os
import re
from pathlib import Path

import pdfplumber

from licitasuite.models.fornecedor import Fornecedor, ItemFornecedor
from licitasuite.parsers.text_utils import normalize_text, parse_number


# Aceita CNPJ normal e CNPJ quebrado no PDF:
# 03.945.035/0001-
# 91
CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\s*\d{2}")

ITEM_START_RE = re.compile(r"^\s*(?P<codigo>\d{4})\s+(?P<body>.+)")

MONEY_VALUE = r"\d{1,3}(?:\.\d{3})*,\d{2,4}|\d+,\d{2,4}"

MONEY_RE = re.compile(
    rf"(?P<qtd>\d{{1,3}}(?:\.\d{{3}})*|\d+)\s+"
    rf"(?P<un>[A-ZÇ]{{2,8}})\s+"
    rf"R\$\s*(?P<unit>{MONEY_VALUE})\s+"
    rf"R\$\s*(?P<total>{MONEY_VALUE})"
)

TOTAL_RE = re.compile(
    rf"TOTAL\s+DO\s+VENCEDOR\s+R\$\s*(?P<total>{MONEY_VALUE})",
    flags=re.I,
)

SUPPLIER_RE = re.compile(
    r"(?P<name>.+?)\s*\|\s*Tipo:\s*(?P<tipo>.*?)-\s*LC123:.*?Documento\s+"
    r"(?P<cnpj>\d{2}\.\d{3}\.\d{3}/\d{4}-\s*\d{2})",
    flags=re.I | re.S,
)

HEADER_RE = re.compile(r"(?m)^\s*(.+?)\s+\|\s*Tipo:", flags=re.I)

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

        if not suppliers:
            suppliers = self._parse_legacy_lines(text)

        suppliers = self._apply_manual_supplier_locations(text, suppliers)

        # Relatório simples de conferência do parser.
        self._write_parser_audit(suppliers)

        return suppliers

    # ------------------------------------------------------------------
    # Auditoria de valores
    # ------------------------------------------------------------------

    def _write_parser_audit(self, suppliers):
        Path("output").mkdir(exist_ok=True)
        lines = []
        for fornecedor in suppliers:
            soma = sum(float(getattr(item, "valor_total", 0) or 0) for item in fornecedor.itens)
            lines.append(f"{fornecedor.razao_social} | itens: {len(fornecedor.itens)} | soma_itens: {soma:.4f}")
            for item in fornecedor.itens:
                origem = getattr(item, "linha_origem", "") or ""
                if "VALOR_TOTAL_NAO_DETECTADO" in origem or "DIVERGENCIA_TOTAL_FORNECEDOR" in origem:
                    lines.append(f"  ALERTA item {item.numero_item}: {origem}")
        (Path("output") / "auditoria_valores_pdf.txt").write_text("\n".join(lines), encoding="utf-8")

    # ------------------------------------------------------------------
    # Localização manual
    # ------------------------------------------------------------------

    def _manual_names(self):
        raw = os.environ.get("LICITASUITE_FORNECEDORES_MANUAIS", "").strip()
        if not raw:
            return []

        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except Exception:
            pass

        names = []
        for line in raw.splitlines():
            line = line.strip(" -•\t")
            if line:
                names.append(line)
        return names

    def _apply_manual_supplier_locations(self, text, suppliers):
        manual_names = self._manual_names()
        if not manual_names:
            return suppliers

        existing = {self._supplier_key(s.razao_social) for s in suppliers}
        text_prepared = self._prepare_text(text)

        for name in manual_names:
            key = self._supplier_key(name)
            if not key or key in existing:
                continue

            block = self._find_manual_block(text_prepared, name)
            if not block:
                continue

            fornecedor = self._parse_supplier_block(block)

            if not fornecedor:
                fornecedor = self._make_supplier_from_manual_name(block, name)

            if fornecedor:
                fornecedor.itens = self._parse_item_rows_from_block(block)
                if fornecedor.itens:
                    suppliers.append(fornecedor)
                    existing.add(self._supplier_key(fornecedor.razao_social))

        return suppliers

    def _find_manual_block(self, text, name):
        idx = self._find_name_index(text, name)
        if idx < 0:
            return ""

        next_header = HEADER_RE.search(text, idx + 10)
        end = next_header.start() if next_header else len(text)
        return text[idx:end].strip()

    def _find_name_index(self, text, name):
        norm_text = self._norm_for_search(text)
        norm_name = self._norm_for_search(name)

        tokens = [t for t in re.split(r"\W+", norm_name) if len(t) >= 3]
        if not tokens:
            return -1

        # Busca literal aproximada pelas duas primeiras palavras significativas.
        if len(tokens) >= 2:
            first_two = " ".join(tokens[:2])
            idx_norm = norm_text.find(first_two)
            if idx_norm >= 0:
                first = tokens[0]
                m = re.search(first, self._norm_for_search(text), flags=re.I)
                if m:
                    return max(0, m.start() - 120)

        first = tokens[0]
        m = re.search(first, self._norm_for_search(text), flags=re.I)
        if m:
            return max(0, m.start() - 120)

        return -1

    def _make_supplier_from_manual_name(self, block, name):
        cnpj = ""
        cnpj_m = CNPJ_RE.search(block)
        if cnpj_m:
            cnpj = re.sub(r"\s+", "", cnpj_m.group(0))

        tipo = self._between(block, "| Tipo:", "- LC123")

        return Fornecedor(
            razao_social=name,
            cnpj=cnpj,
            tipo=tipo,
            endereco=self._between(block, "Endereço:", "CEP:"),
            cep=self._between(block, "CEP:", "UF:"),
            uf=self._between(block, "UF:", "Município:"),
            municipio=self._between(block, "Município:", "Telefone:"),
            telefone=self._after(block, "Telefone:"),
        )

    def _supplier_key(self, name):
        n = self._norm_for_search(name)
        n = re.sub(
            r"\b(LTDA|EIRELI|SA|S A|ME|EPP|SS|COMERCIO|DISTRIBUIDORA|DISTRIBUICAO|MEDICAMENTOS|PRODUTOS)\b",
            " ",
            n,
        )
        n = re.sub(r"\s+", " ", n).strip()
        return n

    def _norm_for_search(self, value):
        value = value or ""
        value = value.upper()
        value = value.replace("Á", "A").replace("À", "A").replace("Â", "A").replace("Ã", "A")
        value = value.replace("É", "E").replace("Ê", "E")
        value = value.replace("Í", "I")
        value = value.replace("Ó", "O").replace("Ô", "O").replace("Õ", "O")
        value = value.replace("Ú", "U")
        value = value.replace("Ç", "C")
        value = re.sub(r"[^A-Z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    # ------------------------------------------------------------------
    # Parser robusto por blocos
    # ------------------------------------------------------------------

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

            # Se a soma não bater com o TOTAL DO VENCEDOR, marca alerta,
            # mas não inventa valor.
            self._mark_total_mismatch_if_needed(fornecedor, block)

            if fornecedor.itens:
                suppliers.append(fornecedor)

        return suppliers

    def _mark_total_mismatch_if_needed(self, fornecedor, block):
        total_m = TOTAL_RE.search(block)
        if not total_m:
            for item in fornecedor.itens:
                item.linha_origem = f"VALOR_TOTAL_DO_FORNECEDOR_NAO_DETECTADO | {item.linha_origem}"
            return

        total_oficial = parse_number(total_m.group("total"))
        soma_itens = sum(float(getattr(item, "valor_total", 0) or 0) for item in fornecedor.itens)

        # tolerância baixa porque os valores têm 4 casas.
        if abs(total_oficial - soma_itens) > 0.05:
            for item in fornecedor.itens:
                item.linha_origem = (
                    f"DIVERGENCIA_TOTAL_FORNECEDOR: total oficial PDF R$ {total_oficial:.4f}; "
                    f"soma itens extraídos R$ {soma_itens:.4f} | {item.linha_origem}"
                )

    def _prepare_text(self, text):
        text = text or ""
        text = text.replace("\xa0", " ")
        text = text.replace("\u00ad", "")
        text = text.replace("\ufffe", "")
        text = text.replace("OTO\ufffeBETNOVATE", "OTO-BETNOVATE")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _parse_supplier_block(self, block):
        first_part = block[:1800]
        m = SUPPLIER_RE.search(first_part)

        if not m:
            return None

        line = " ".join(block.splitlines()[:8])
        line = " ".join(line.split())

        name = re.sub(r"\s+", " ", m.group("name")).strip(" -|")
        tipo = re.sub(r"\s+", " ", m.group("tipo")).strip(" -|")
        cnpj = re.sub(r"\s+", "", m.group("cnpj"))

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
        total_m = TOTAL_RE.search(block)
        total_start = total_m.start() if total_m else len(block)

        item_starts = list(re.finditer(r"(?m)^\s*(\d{4})\s+.+", block[:total_start]))

        items = []
        seen = set()

        for idx, m in enumerate(item_starts):
            start = m.start()
            end = item_starts[idx + 1].start() if idx + 1 < len(item_starts) else total_start
            segment = block[start:end].strip()

            item = self._parse_item_segment(segment)
            if item and item.numero_item not in seen:
                items.append(item)
                seen.add(item.numero_item)

        return items

    def _parse_item_segment(self, segment):
        flat = " ".join(segment.split())
        m = ITEM_START_RE.match(flat)
        if not m:
            return None

        numero = int(m.group("codigo"))
        body = m.group("body")

        # Caso normal: quantidade/unidade + valor unitário + valor total.
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
                linha_origem=flat,
            )

        # Caso quebrado: no PDF o valor total aparece depois do segundo "R$",
        # mas pode haver descrição/código entre o R$ e o número.
        m2 = re.search(
            rf"(?P<qtd>\d{{1,3}}(?:\.\d{{3}})*|\d+)\s+"
            rf"(?P<un>[A-ZÇ]{{2,8}})\s+"
            rf"R\$\s*(?P<unit>{MONEY_VALUE})\s+R\$\s*(?P<after>.*)$",
            body,
            flags=re.I,
        )
        if m2:
            after = m2.group("after")
            values_after = re.findall(MONEY_VALUE, after)

            if values_after:
                qtd = parse_number(m2.group("qtd"))
                unit = parse_number(m2.group("unit"))
                total = parse_number(values_after[-1])
                before = body[:m2.start()].strip()
                marca = self._guess_brand(before)

                return ItemFornecedor(
                    numero_item=numero,
                    marca=marca,
                    quantidade_pdf=qtd,
                    valor_unitario=unit,
                    valor_total=total,
                    linha_origem=flat,
                )

        # Caso alternativo: encontra os valores com R$ em qualquer posição.
        values = re.findall(rf"R\$\s*({MONEY_VALUE})", body)
        qtd_un = re.search(rf"(\d{{1,3}}(?:\.\d{{3}})*|\d+)\s+([A-ZÇ]{{2,8}})\s+R\$", body)

        if values and qtd_un:
            qtd = parse_number(qtd_un.group(1))
            unit = parse_number(values[-2]) if len(values) >= 2 else 0
            total = parse_number(values[-1])
            before = body[:qtd_un.start()].strip()
            marca = self._guess_brand(before)

            return ItemFornecedor(
                numero_item=numero,
                marca=marca,
                quantidade_pdf=qtd,
                valor_unitario=unit,
                valor_total=total,
                linha_origem=flat,
            )

        # Último fallback: não inventa valor.
        # Mantém item com valor 0 e marca claramente para conferência manual.
        return ItemFornecedor(
            numero_item=numero,
            marca=self._guess_brand(body),
            quantidade_pdf=0,
            valor_unitario=0,
            valor_total=0,
            linha_origem=f"VALOR_TOTAL_NAO_DETECTADO_MANUALMENTE | {flat}",
        )

    # ------------------------------------------------------------------
    # Parser antigo como fallback
    # ------------------------------------------------------------------

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
            return False

        return True

    def _parse_supplier(self, line):
        cnpj = re.sub(r"\s+", "", CNPJ_RE.search(line).group(0))
        before_cnpj = line.split(CNPJ_RE.search(line).group(0), 1)[0]
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
            item = self._parse_item_segment(row)
            if item and item.numero_item not in seen:
                items.append(item)
                seen.add(item.numero_item)

        return items

    def _guess_brand(self, text):
        text = re.sub(r"\([^)]*CONFORME EDITAL[^)]*\)", "", text, flags=re.I)
        parts = text.split()

        if len(parts) <= 4:
            return " ".join(parts)

        return " ".join(parts[-4:])
