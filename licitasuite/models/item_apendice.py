from dataclasses import dataclass, field
from typing import Any

@dataclass
class ItemApendice:
    numero_item: int
    codigo_siplan: str
    descricao: str
    apresentacao: str
    total: float = 0.0
    cells_text: list[str] = field(default_factory=list)
    raw_row_xml: Any = None
