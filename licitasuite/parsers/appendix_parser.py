from pathlib import Path
from copy import deepcopy
from docx import Document
from licitasuite.models.item_apendice import ItemApendice
from licitasuite.parsers.text_utils import normalize_text, parse_number
from licitasuite.core.exceptions import AppendixParserError

class AppendixParser:
    def parse(self, path):
        path = Path(path)
        if not path.exists():
            raise AppendixParserError("Apêndice não localizado.")

        doc = Document(path)

        for table in doc.tables:
            header_index, mapping = self._detect_header(table)
            if mapping:
                return self._read_table(table, header_index, mapping)

        raise AppendixParserError("Tabela do Apêndice não localizada.")

    def _detect_header(self, table):
        for i, row in enumerate(table.rows):
            headers = [normalize_text(cell.text) for cell in row.cells]
            mapping = {}

            for idx, h in enumerate(headers):
                if "SIPLAN" in h or "CODIGO" in h or "CÓDIGO" in h:
                    mapping.setdefault("codigo", idx)
                elif h == "ITEM" or " ITEM" in h:
                    mapping.setdefault("item", idx)
                elif "DESCRIT" in h or "DESCRICAO" in h or "DESCRIÇÃO" in h:
                    mapping.setdefault("descricao", idx)
                elif "APRESENT" in h or "UNIDADE" in h:
                    mapping.setdefault("apresentacao", idx)
                elif h == "TOTAL" or h.endswith("TOTAL"):
                    mapping.setdefault("total", idx)

            if {"codigo", "item", "descricao", "apresentacao"}.issubset(mapping):
                if "total" not in mapping:
                    mapping["total"] = len(headers) - 1
                return i, mapping

        return None, None

    def _read_table(self, table, header_index, mapping):
        itens = []

        for row in table.rows[header_index + 1:]:
            cells = [cell.text.strip() for cell in row.cells]

            if len(cells) <= max(mapping.values()):
                continue

            digits = "".join(ch for ch in cells[mapping["item"]] if ch.isdigit())
            if not digits:
                continue

            itens.append(ItemApendice(
                numero_item=int(digits),
                codigo_siplan=cells[mapping["codigo"]],
                descricao=cells[mapping["descricao"]],
                apresentacao=cells[mapping["apresentacao"]],
                total=parse_number(cells[mapping["total"]]),
                cells_text=cells,
                raw_row_xml=deepcopy(row._tr),
            ))

        return itens
