from dataclasses import dataclass, field

@dataclass
class AtaItem:
    numero_item: int
    codigo_siplan: str
    descricao_oficial: str
    apresentacao: str
    marca: str = ""
    fabricante: str = ""
    modelo: str = ""
    quantidade: float = 0.0
    valor_unitario: float = 0.0
    valor_total: float = 0.0
    appendix_cells_text: list[str] = field(default_factory=list)

@dataclass
class AtaData:
    fornecedor_nome: str
    fornecedor_cnpj: str
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
    itens: list[AtaItem] = field(default_factory=list)
    informacoes_nao_localizadas: list[str] = field(default_factory=list)
    inconsistencias: list[str] = field(default_factory=list)

    @property
    def valor_total(self):
        return sum(item.valor_total for item in self.itens)
