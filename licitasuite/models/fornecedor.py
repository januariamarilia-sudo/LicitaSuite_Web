from dataclasses import dataclass, field

@dataclass
class ItemFornecedor:
    numero_item: int
    marca: str = ""
    fabricante: str = ""
    modelo: str = ""
    quantidade: float = 0.0
    valor_unitario: float = 0.0
    valor_total: float = 0.0
    linha_origem: str = ""

@dataclass
class Fornecedor:
    razao_social: str
    cnpj: str = ""
    endereco: str = ""
    municipio: str = ""
    uf: str = ""
    cep: str = ""
    telefone: str = ""
    email: str = ""
    representante: str = ""
    cpf_representante: str = ""
    rg_representante: str = ""
    itens: list[ItemFornecedor] = field(default_factory=list)
