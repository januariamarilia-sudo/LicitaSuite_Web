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

    text = re.sub(r"[^0-9,.-]", "", text)
    if not text:
        return 0.0

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
        try:
            return float(text)
        except Exception:
            return 0.0

    if "." in text:
        parts = text.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
            try:
                return float("".join(parts))
            except Exception:
                return 0.0
        try:
            return float(text)
        except Exception:
            return 0.0

    try:
        return float(text)
    except Exception:
        return 0.0

def format_money(value, casas=2):
    value = float(value or 0)
    s = f"R$ {value:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def format_qty(value, use_thousands=False):
    value = float(value or 0)
    if use_thousands:
        s = f"{int(round(value)):,.0f}"
        return s.replace(",", ".")
    if value.is_integer():
        return str(int(value))
    return str(value).replace(".", ",")

def safe_filename(text):
    text = "" if text is None else str(text)
    text = re.sub(r'[\\/:*?"<>|]+', " ", text)
    text = " ".join(text.split()).strip()
    return text[:150]
