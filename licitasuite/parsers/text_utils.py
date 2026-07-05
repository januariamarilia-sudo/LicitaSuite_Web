import re
import unicodedata

def normalize_text(text):
    text = "" if text is None else str(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.upper().split())

def parse_number(value):
    if value is None:
        return 0.0
    text = str(value).strip()
    text = text.replace("R$", "").replace(" ", "")
    if not text:
        return 0.0
    # padrão brasileiro: 1.234,5678
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        digits = re.sub(r"[^0-9.]", "", text)
        try:
            return float(digits)
        except Exception:
            return 0.0
