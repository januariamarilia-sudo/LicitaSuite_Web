from dataclasses import dataclass, field
from licitasuite.models.ata_item import AtaItem

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
    inconsistencias: list[str] = field(default_factory=list)
    informacoes_nao_localizadas: list[str] = field(default_factory=list)

    @property
    def valor_total(self):
        return sum(item.valor_total for item in self.itens)
