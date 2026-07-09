from urllib.parse import urlencode


PORTAL_PROCESS_SEARCH_URL = (
    "https://www.portaldecompraspublicas.com.br/processos"
)
PORTAL_PARTNERS_URL = "https://www.portaldecompraspublicas.com.br/parceiros"


def build_process_search_url(process_number: str, agency: str = "ICISMEP") -> str:
    params = {}
    if process_number.strip():
        params["processo"] = process_number.strip()
    if agency.strip():
        params["orgao"] = agency.strip()
    return f"{PORTAL_PROCESS_SEARCH_URL}?{urlencode(params)}"
