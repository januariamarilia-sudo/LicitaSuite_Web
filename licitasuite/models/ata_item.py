from dataclasses import dataclass
from typing import Any

@dataclass
class AtaItem:
    numero_item: int
    codigo_siplan: str
    descricao_oficial: str
    apresentacao: str
    marca: str
    fabricante: str
    modelo: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    appendix_cells_text: list[str] | None = None
    appendix_row_xml: Any = None
