from decimal import Decimal, ROUND_HALF_UP
import re

BLANK_FIELD = "____________________________"

def missing_if_blank(value):
    text = "" if value is None else str(value).strip()
    if text.lower() in ["nan", "none", "null"]:
        text = ""
    return text or BLANK_FIELD

def only_digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())

def format_brl(value, decimals=2):
    q = Decimal(str(value or 0)).quantize(Decimal("1." + ("0" * decimals)), rounding=ROUND_HALF_UP)
    integer, decimal = f"{q:.{decimals}f}".split(".")
    integer = f"{int(integer):,}".replace(",", ".")
    return f"R$ {integer},{decimal}"

def format_quantity(value):
    try:
        value = float(value or 0)
    except Exception:
        return str(value)
    if value.is_integer():
        return str(int(value))
    return str(value).replace(".", ",")

def safe_filename(value):
    value = str(value or "FORNECEDOR")
    value = re.sub(r'[\\\\/:*?"<>|]', "", value)
    value = re.sub(r"\\s+", " ", value).strip()
    return value[:150]
