import re
import unicodedata

def normalize_text(value):
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.upper()
    value = re.sub(r"\s+", " ", value)
    return value.strip()

def parse_number(value):
    text = "" if value is None else str(value).strip()
    if not text:
        return 0.0
    text = re.sub(r"[^0-9,.-]", "", text)
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        return 0.0
