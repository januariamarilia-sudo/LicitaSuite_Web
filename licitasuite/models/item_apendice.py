from dataclasses import dataclass, field

@dataclass
class ItemApendice:
    numero_item: int
    codigo_siplan: str
    descricao: str
    apresentacao: str
    municipios: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    cells_text: list[str] = field(default_factory=list)
