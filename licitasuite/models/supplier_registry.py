from dataclasses import dataclass

@dataclass
class SupplierRegistry:
    razao_social: str = ""
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
