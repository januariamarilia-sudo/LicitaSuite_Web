from dataclasses import dataclass, field

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
    appendix_cells_text: list[str] = field(default_factory=list)
