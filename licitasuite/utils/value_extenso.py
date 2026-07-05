from decimal import Decimal, ROUND_HALF_UP
from num2words import num2words

def valor_por_extenso(valor):
    q = Decimal(str(valor or 0)).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
    inteiro = int(q)
    centavos = int((q - Decimal(inteiro)) * 100)

    partes = []
    partes.append("um real" if inteiro == 1 else num2words(inteiro, lang="pt_BR") + " reais")

    if centavos:
        partes.append("um centavo" if centavos == 1 else num2words(centavos, lang="pt_BR") + " centavos")

    return " e ".join(partes)
