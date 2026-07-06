from pathlib import Path
from docx import Document
from licitasuite.models.item_apendice import ItemApendice
from licitasuite.parsers.text_utils import normalize_text, parse_number

class AppendixParser:
    def parse(self, path):
        path = Path(path)
        doc = Document(path)
        for table in doc.tables:
            header_idx, mapping, mode = self._find_header(table)
            if mapping:
                return self._read_items(table, header_idx, mapping, mode)
        raise RuntimeError("Tabela do Apêndice não localizada.")

    def _find_header(self, table):
        for i, row in enumerate(table.rows[:8]):
            headers = [normalize_text(c.text) for c in row.cells]
            mapping = {}
            mode = "siplan"
            for idx, h in enumerate(headers):
                if h == "LOTE" or h.startswith("LOTE "):
                    mapping["lote"] = idx
                    mode = "lote"
                elif ("SIPLAN" in h or "COD" in h) and "codigo" not in mapping and "LOTE" not in h:
                    mapping["codigo"] = idx
                elif h == "ITEM" or h.endswith(" ITEM"):
                    mapping["item"] = idx
                elif "DESCRIT" in h or "DESCRICAO" in h:
                    mapping["descricao"] = idx
                elif "APRESENT" in h:
                    mapping["apresentacao"] = idx
                elif h == "TOTAL" or "DEMANDA" in h or h.endswith("CONSORCIADOS"):
                    mapping["total"] = idx

            if mode == "lote" and {"lote", "item", "descricao", "apresentacao", "total"}.issubset(mapping):
                return i, mapping, "lote"
            if {"codigo", "item", "descricao", "apresentacao", "total"}.issubset(mapping):
                return i, mapping, "siplan"
        return None, None, None

    def _digits_int(self, text):
        digits = "".join(ch for ch in str(text) if ch.isdigit())
        return int(digits) if digits else None

    def _read_items(self, table, header_idx, mapping, mode):
        itens = []
        for row in table.rows[header_idx + 1:]:
            cells = [c.text.strip() for c in row.cells]
            if len(cells) <= max(mapping.values()):
                continue

            item_num = self._digits_int(cells[mapping["item"]])
            if item_num is None:
                continue

            if mode == "lote":
                lote_num = self._digits_int(cells[mapping["lote"]])
                if lote_num is None:
                    continue
                unique = lote_num * 10000 + item_num
                codigo = cells[mapping["lote"]] or f"LOTE {lote_num}"
                itens.append(ItemApendice(
                    numero_item=unique,
                    codigo_siplan=codigo,
                    descricao=cells[mapping["descricao"]],
                    apresentacao=cells[mapping["apresentacao"]],
                    total=parse_number(cells[mapping["total"]]),
                    cells_text=cells,
                    lote=lote_num,
                    item_display=str(item_num),
                    lote_display=str(lote_num),
                ))
            else:
                itens.append(ItemApendice(
                    numero_item=item_num,
                    codigo_siplan=cells[mapping["codigo"]],
                    descricao=cells[mapping["descricao"]],
                    apresentacao=cells[mapping["apresentacao"]],
                    total=parse_number(cells[mapping["total"]]),
                    cells_text=cells,
                    item_display=str(item_num),
                ))
        return itens
