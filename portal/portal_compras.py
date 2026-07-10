from html import unescape
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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


def _html_to_lines(html: str) -> list[str]:
    html = re.sub(r"(?is)<script.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?</style>", " ", html)
    html = re.sub(r"(?is)<[^>]+>", "\n", html)
    text = unescape(html)
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if re.sub(r"\s+", " ", line).strip()
    ]


def extract_supplier_names_from_process_page(html: str) -> list[str]:
    lines = _html_to_lines(html)
    try:
        start = next(
            index for index, line in enumerate(lines)
            if line.casefold() == "fornecedores"
        )
    except StopIteration:
        return []

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].casefold() in {"itens", "item 1"}:
            end = index
            break

    ignored = {
        "processo",
        "fornecedores",
        "baixar tudo",
        "buscar documento",
        "documentos",
        "download concluído",
        "download concluido",
    }
    suppliers: list[str] = []
    seen: set[str] = set()
    for line in lines[start + 1:end]:
        normalized = line.casefold().strip()
        if normalized in ignored:
            continue
        if normalized.isdigit():
            continue
        if len(line) < 4:
            continue
        if normalized.startswith("página") or normalized.startswith("pagina"):
            continue
        if normalized not in seen:
            suppliers.append(line)
            seen.add(normalized)
    return suppliers


def fetch_supplier_names_from_process_url(url: str, timeout: int = 20) -> list[str]:
    if not url.startswith("https://www.portaldecompraspublicas.com.br/processos/"):
        raise ValueError("Cole um link público de processo do Portal de Compras Públicas.")
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8", errors="replace")
    return extract_supplier_names_from_process_page(html)
