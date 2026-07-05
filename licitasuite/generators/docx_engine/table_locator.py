import unicodedata
import re

def normalize(value):
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.upper()
    value = re.sub(r"\s+", " ", value)
    return value.strip()

class TableLocator:
    """
    Localiza tabelas do modelo por palavras-chave.
    """

    def find_table(self, document, required_words):
        required = [normalize(w) for w in required_words]

        for table in document.tables:
            text = self.table_text(table)
            if all(word in text for word in required):
                return table

        return None

    def table_text(self, table):
        return normalize(" ".join(cell.text for row in table.rows for cell in row.cells))
