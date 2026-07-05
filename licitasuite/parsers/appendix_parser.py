from pathlib import Path
from docx import Document
from licitasuite.models.item_apendice import ItemApendice
from licitasuite.parsers.text_utils import normalize_text, parse_number

class AppendixParser:
    def parse(self, path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError("Apêndice não localizado.")

        doc = Document(path)

        for table in doc.tables:
            header_index, mapping = self._detect_header(table)
            if mapping:
                return self._read_table(table, header_index, mapping)

        raise RuntimeError("Tabela do Apêndice não localizada.")

    def _detect_header(self, table):
        for i, row in enumerate(table.rows[:5]):
            headers = [normalize_text(cell.text) for cell in row.cells]
            mapping = {}
            for idx, h in enumerate(headers):
                if ("SIPLAN" in h or "CODIGO" in h) and "codigo" not in mapping:
                    mapping["codigo"] = idx
                elif h == "ITEM" or h.endswith(" ITEM") or "ITEM" == h:
                    mapping["item"] = idx
                elif "DESCRIT" in h or "DESCRICAO" in h:
                    mapping["descricao"] = idx
                elif "APRESENT" in h:
                    mapping["apresentacao"] = idx
                elif h == "TOTAL" or h.endswith("TOTAL") or "DEMANDA" in h:
                    mapping["total"] = idx

            if {"codigo", "item", "descricao", "apresentacao", "total"}.issubset(mapping):
                return i, mapping

        return None, None

    def _read_table(self, table, header_index, mapping):
        itens = []
        for row in table.rows[header_index + 1:]:
            cells = [cell.text.strip() for cell in row.cells]
            if len(cells) <= max(mapping.values()):
                continue

            item_text = cells[mapping["item"]]
            digits = "".join(ch for ch in item_text if ch.isdigit())
            if not digits:
                continue

            itens.append(ItemApendice(
                numero_item=int(digits),
                codigo_siplan=cells[mapping["codigo"]],
                descricao=cells[mapping["descricao"]],
                apresentacao=cells[mapping["apresentacao"]],
                total=parse_number(cells[mapping["total"]]),
                cells_text=cells,
            ))

        return itens
