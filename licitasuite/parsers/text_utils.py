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
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if not text:
        return 0.0
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = re.sub(r"[^0-9.]", "", text)
    try:
        return float(text)
    except Exception:
        return 0.0

def format_money(value, casas=2):
    value = float(value or 0)
    s = f"R$ {value:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def format_qty(value):
    value = float(value or 0)
    if value.is_integer():
        return str(int(value))
    return str(value).replace(".", ",")

def safe_filename(text):
    text = "" if text is None else str(text)
    text = re.sub(r'[\\/:*?"<>|]+', " ", text)
    return " ".join(text.split()).strip()[:150]
