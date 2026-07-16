from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, Optional

from docx import Document

from licitasuite.models.item_apendice import ItemApendice
from licitasuite.parsers.text_utils import normalize_text, parse_number


@dataclass
class TableProfile:
    index: int
    table: object
    rows: int
    cols: int
    header_idx: Optional[int] = None
    mapping: Dict[str, int] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    score: int = 0
    numeric_item_rows: int = 0
    fallback: bool = False


class AppendixParser:
    HEADER_SCAN_ROWS = 15
    MIN_HEADER_SCORE = 8

    def __init__(self):
        self.diagnostics = []

    def parse(self, path):
        path = Path(path)
        doc = Document(path)
        profiles = [self._profile_table(i, table) for i, table in enumerate(doc.tables, start=1)]
        selected = self._select_table(profiles)
        self.diagnostics = self._build_diagnostics(profiles, selected)

        if not selected:
            raise RuntimeError("Tabela do Apendice nao localizada.")

        itens = self._read_items(selected.table, selected.header_idx or 0, selected.mapping)
        if not itens:
            raise RuntimeError("Tabela do Apendice localizada, mas sem linhas de itens numericos.")
        return itens

    def _profile_table(self, index, table):
        rows = len(table.rows)
        cols = max((len(row.cells) for row in table.rows), default=0)
        best = TableProfile(index=index, table=table, rows=rows, cols=cols)

        for row_idx in range(min(rows, self.HEADER_SCAN_ROWS)):
            mapping, headers = self._map_headers(table, row_idx)
            numeric_rows = self._count_numeric_item_rows(table, row_idx, mapping.get("item"))
            score = self._score_mapping(mapping, numeric_rows) + self._current_header_hits(table, row_idx, mapping)
            if score > best.score:
                best.header_idx = row_idx
                best.mapping = mapping
                best.headers = headers
                best.score = score
                best.numeric_item_rows = numeric_rows

        if best.score < self.MIN_HEADER_SCORE:
            fallback = self._fallback_profile(index, table, rows, cols)
            if fallback and fallback.numeric_item_rows > best.numeric_item_rows:
                return fallback
        return best

    def _map_headers(self, table, row_idx):
        max_cols = max((len(row.cells) for row in table.rows), default=0)
        mapping = {}
        headers = {}
        rows = self._context_rows(table, row_idx)
        current_cells = self._row_texts(table.rows[row_idx])

        for col_idx in range(max_cols):
            parts = []
            current_text = ""
            for row in rows:
                cells = self._row_texts(row)
                if col_idx < len(cells) and cells[col_idx]:
                    parts.append(cells[col_idx])
            if col_idx < len(current_cells):
                current_text = normalize_text(current_cells[col_idx])
            text = normalize_text(" ".join(parts))
            key = self._header_key(text)
            if key and key not in mapping:
                mapping[key] = col_idx
                headers[key] = current_text if self._header_key(current_text) == key else text

        return mapping, headers

    def _current_header_hits(self, table, row_idx, mapping):
        if not mapping:
            return 0
        hits = 0
        cells = self._row_texts(table.rows[row_idx])
        for key, col_idx in mapping.items():
            if col_idx < len(cells) and self._header_key(normalize_text(cells[col_idx])) == key:
                hits += 1
        return hits

    def _context_rows(self, table, row_idx):
        start = max(0, row_idx - 1)
        end = min(len(table.rows), row_idx + 2)
        return list(table.rows[start:end])

    def _header_key(self, text):
        if not text:
            return None

        if self._is_item_header(text):
            return "item"
        if any(word in text for word in ["DESCRICAO", "DESCRITIVO", "ESPECIFICACAO", "OBJETO"]):
            return "descricao"
        if any(word in text for word in ["UNIDADE", "UNID", "UND", "APRESENTACAO"]):
            return "apresentacao"
        if any(word in text for word in ["QUANTIDADE", "QUANT", "QTD", "QUANTITATIVO", "TOTAL", "DEMANDA", "CONSORCIADO"]):
            return "total"
        if "SIPLAN" in text or re.search(r"\b(CODIGO|COD)\b", text):
            return "codigo"
        return None

    def _is_item_header(self, text):
        if text == "ITEM":
            return True
        if "ITEM" not in text:
            return False
        if any(word in text for word in ["DESCRICAO", "CODIGO", "COD", "SIPLAN"]):
            return False
        return bool(re.search(r"(^|\b)(N|NO|NUMERO)?\s*ITEM(\b|$)", text))

    def _score_mapping(self, mapping, numeric_rows):
        score = 0
        if "item" in mapping:
            score += 4
        if "descricao" in mapping:
            score += 3
        if "codigo" in mapping:
            score += 2
        if "total" in mapping:
            score += 2
        if "apresentacao" in mapping:
            score += 1
        if {"item", "descricao"}.issubset(mapping):
            score += 2
        if numeric_rows:
            score += min(3, numeric_rows)
        return score

    def _select_table(self, profiles):
        strong = [
            p for p in profiles
            if p.score >= self.MIN_HEADER_SCORE
            and "item" in p.mapping
            and ("descricao" in p.mapping or "codigo" in p.mapping)
            and p.numeric_item_rows > 0
        ]
        if strong:
            return max(strong, key=lambda p: (p.score, p.numeric_item_rows, p.rows * p.cols))

        fallback = [
            p for p in profiles
            if p.fallback and p.numeric_item_rows > 0 and "item" in p.mapping
        ]
        if fallback:
            return max(fallback, key=lambda p: (p.numeric_item_rows, p.rows * p.cols))
        return None

    def _fallback_profile(self, index, table, rows, cols):
        if rows < 2 or cols < 2:
            return None

        item_col, numeric_rows = self._infer_item_column(table, 0)
        if item_col is None or numeric_rows == 0:
            return None

        item_rows = self._item_rows(table, 0, item_col)
        if not item_rows:
            return None

        mapping = {"item": item_col}
        descricao_col = self._infer_description_column(item_rows, item_col)
        if descricao_col is not None:
            mapping["descricao"] = descricao_col

        total_col = self._infer_total_column(item_rows, item_col, descricao_col)
        if total_col is not None:
            mapping["total"] = total_col

        codigo_col = self._infer_code_column(item_rows, item_col)
        if codigo_col is not None:
            mapping["codigo"] = codigo_col

        apresentacao_col = self._infer_short_text_column(item_rows, item_col, descricao_col, total_col, codigo_col)
        if apresentacao_col is not None:
            mapping["apresentacao"] = apresentacao_col

        headers = {key: f"COLUNA {col + 1}" for key, col in mapping.items()}
        return TableProfile(
            index=index,
            table=table,
            rows=rows,
            cols=cols,
            header_idx=0,
            mapping=mapping,
            headers=headers,
            score=self._score_mapping(mapping, numeric_rows),
            numeric_item_rows=numeric_rows,
            fallback=True,
        )

    def _infer_item_column(self, table, header_idx):
        counts = {}
        for row in table.rows[header_idx + 1:]:
            for col_idx, text in enumerate(self._row_texts(row)):
                if self._item_number(text) is not None:
                    counts[col_idx] = counts.get(col_idx, 0) + 1
        if not counts:
            return None, 0
        return max(counts.items(), key=lambda item: item[1])

    def _infer_description_column(self, rows, item_col):
        scores = {}
        for row in rows:
            cells = self._row_texts(row)
            for col_idx, text in enumerate(cells):
                if col_idx == item_col:
                    continue
                normalized = normalize_text(text)
                if not normalized or self._item_number(text) is not None:
                    continue
                scores[col_idx] = scores.get(col_idx, 0) + len(normalized)
        if not scores:
            return None
        return max(scores.items(), key=lambda item: item[1])[0]

    def _infer_total_column(self, rows, item_col, descricao_col):
        counts = {}
        for row in rows:
            cells = self._row_texts(row)
            for col_idx, text in enumerate(cells):
                if col_idx in [item_col, descricao_col]:
                    continue
                if parse_number(text) > 0:
                    counts[col_idx] = counts.get(col_idx, 0) + 1
        if not counts:
            return None
        return max(counts.items(), key=lambda item: (item[1], item[0]))[0]

    def _infer_code_column(self, rows, item_col):
        counts = {}
        for row in rows:
            cells = self._row_texts(row)
            for col_idx, text in enumerate(cells):
                if col_idx == item_col:
                    continue
                compact = re.sub(r"\D", "", text or "")
                if len(compact) >= 3:
                    counts[col_idx] = counts.get(col_idx, 0) + 1
        if not counts:
            return None
        return max(counts.items(), key=lambda item: item[1])[0]

    def _infer_short_text_column(self, rows, *used_cols):
        used = {col for col in used_cols if col is not None}
        counts = {}
        for row in rows:
            cells = self._row_texts(row)
            for col_idx, text in enumerate(cells):
                normalized = normalize_text(text)
                if col_idx in used or not normalized:
                    continue
                if 1 <= len(normalized.split()) <= 4 and not re.search(r"\d{4,}", normalized):
                    counts[col_idx] = counts.get(col_idx, 0) + 1
        if not counts:
            return None
        return max(counts.items(), key=lambda item: item[1])[0]

    def _count_numeric_item_rows(self, table, header_idx, item_col):
        if item_col is None:
            return 0
        return len(self._item_rows(table, header_idx, item_col))

    def _item_rows(self, table, header_idx, item_col):
        rows = []
        for row in table.rows[header_idx + 1:]:
            cells = self._row_texts(row)
            if item_col < len(cells) and self._item_number(cells[item_col]) is not None:
                rows.append(row)
        return rows

    def _read_items(self, table, header_idx, mapping):
        itens = []
        seen_items = set()
        for row in table.rows[header_idx + 1:]:
            cells = self._row_texts(row)
            item_raw = self._cell(cells, mapping.get("item"))
            numero_item = self._item_number(item_raw)
            if numero_item is None or numero_item in seen_items:
                continue
            seen_items.add(numero_item)
            itens.append(ItemApendice(
                numero_item=numero_item,
                codigo_siplan=self._cell(cells, mapping.get("codigo")),
                descricao=self._cell(cells, mapping.get("descricao")),
                apresentacao=self._cell(cells, mapping.get("apresentacao")),
                total=parse_number(self._cell(cells, mapping.get("total"))),
                cells_text=cells,
            ))
        return itens

    def _row_texts(self, row):
        texts = []
        seen_cells = set()
        for cell in row.cells:
            cell_id = id(cell._tc)
            if cell_id in seen_cells:
                texts.append("")
                continue
            seen_cells.add(cell_id)
            texts.append(" ".join((cell.text or "").split()))
        return texts

    def _cell(self, cells, idx):
        if idx is None or idx >= len(cells):
            return ""
        return cells[idx].strip()

    def _item_number(self, text):
        normalized = normalize_text(text)
        if not normalized:
            return None
        if re.fullmatch(r"\d{1,4}", normalized):
            return int(normalized)
        match = re.fullmatch(r"ITEM\s*0*(\d{1,4})", normalized)
        if match:
            return int(match.group(1))
        return None

    def _build_diagnostics(self, profiles, selected):
        lines = [f"Diagnostico do Apendice: {len(profiles)} tabela(s) encontrada(s)."]
        for profile in profiles:
            status = "selecionada" if selected is profile else "analisada"
            fallback = " (fallback)" if profile.fallback else ""
            header = "nao reconhecido" if profile.header_idx is None else str(profile.header_idx + 1)
            headers = ", ".join(
                f"{key}=coluna {col + 1} [{profile.headers.get(key, '').strip()}]"
                for key, col in sorted(profile.mapping.items(), key=lambda item: item[1])
            ) or "nenhum"
            lines.append(
                f"- Tabela {profile.index}: {profile.rows} linha(s) x {profile.cols} coluna(s); "
                f"{status}{fallback}; linha de cabecalho: {header}; "
                f"pontuacao: {profile.score}; linhas numericas: {profile.numeric_item_rows}; "
                f"cabecalhos: {headers}"
            )
        return lines
