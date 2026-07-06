from dataclasses import dataclass, field

@dataclass
class ItemFornecedor:
    numero_item: int
    marca: str = ""
    fabricante: str = ""
    modelo: str = ""
    quantidade_pdf: float = 0.0
    valor_unitario: float = 0.0
    valor_total: float = 0.0
    linha_origem: str = ""
    lote: int | None = None
    item_display: str | None = None

@dataclass
class Fornecedor:
    razao_social: str
    cnpj: str = ""
    tipo: str = ""
    endereco: str = ""
    municipio: str = ""
    uf: str = ""
    cep: str = ""
    telefone: str = ""
    email: str = ""
    inscricao_estadual: str = ""
    representante: str = ""
    cpf_representante: str = ""
    rg_representante: str = ""
    orgao_expedidor: str = ""
    itens: list[ItemFornecedor] = field(default_factory=list)
