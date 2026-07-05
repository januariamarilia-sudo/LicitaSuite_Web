from pathlib import Path
from docx import Document
from licitasuite.models.item_apendice import ItemApendice
from licitasuite.parsers.text_utils import normalize_text, parse_number

class AppendixParser:
    def parse(self, path):
        path = Path(path)
        doc = Document(path)
        for table in doc.tables:
            header_idx, mapping = self._find_header(table)
            if mapping:
                return self._read_items(table, header_idx, mapping)
        raise RuntimeError("Tabela do Apêndice não localizada.")

    def _find_header(self, table):
        for i, row in enumerate(table.rows[:8]):
            headers = [normalize_text(c.text) for c in row.cells]
            mapping = {}
            for idx, h in enumerate(headers):
                if ("SIPLAN" in h or "COD" in h) and "codigo" not in mapping:
                    mapping["codigo"] = idx
                elif h == "ITEM" or h.endswith(" ITEM"):
                    mapping["item"] = idx
                elif "DESCRIT" in h or "DESCRICAO" in h:
                    mapping["descricao"] = idx
                elif "APRESENT" in h:
                    mapping["apresentacao"] = idx
                elif h == "TOTAL" or "DEMANDA" in h or h.endswith("CONSORCIADOS"):
                    mapping["total"] = idx
            if {"codigo", "item", "descricao", "apresentacao", "total"}.issubset(mapping):
                return i, mapping
        return None, None

    def _read_items(self, table, header_idx, mapping):
        itens = []
        for row in table.rows[header_idx + 1:]:
            cells = [c.text.strip() for c in row.cells]
            if len(cells) <= max(mapping.values()):
                continue
            item_raw = cells[mapping["item"]]
            digits = "".join(ch for ch in item_raw if ch.isdigit())
            if not digits:
                continue
            itens.append(ItemApendice(
                numero_item=int(digits),
                codigo_siplan=cells[mapping["codigo"]],
                descricao=cells[mapping["descricao"]],
                apresentacao=cells[mapping["apresentacao"]],
                total=parse_number(cells[mapping["total"]]),
                cells_text=cells
            ))
        return itens
