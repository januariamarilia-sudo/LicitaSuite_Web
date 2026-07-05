from pathlib import Path
import pandas as pd
from licitasuite.utils.formatters import only_digits

class SupplierRegistryParser:
    ALIASES = {
        "razao_social": ["razao_social", "razão social", "fornecedor", "empresa", "nome"],
        "cnpj": ["cnpj"],
        "endereco": ["endereco", "endereço", "logradouro"],
        "municipio": ["municipio", "município", "cidade"],
        "uf": ["uf", "estado"],
        "cep": ["cep"],
        "telefone": ["telefone", "fone", "celular"],
        "email": ["email", "e-mail"],
        "representante": ["representante", "representante legal"],
        "cpf_representante": ["cpf_representante", "cpf representante", "cpf"],
        "rg_representante": ["rg_representante", "rg representante", "rg"],
    }

    def parse(self, path):
        if not path:
            return {}

        path = Path(path)
        if not path.exists():
            return {}

        df = pd.read_excel(path)
        normalized = {self._norm(c): c for c in df.columns}
        registry = {}

        for _, row in df.iterrows():
            cnpj = only_digits(self._get(row, normalized, "cnpj"))
            if not cnpj:
                continue

            registry[cnpj] = {
                "razao_social": self._get(row, normalized, "razao_social"),
                "cnpj": cnpj,
                "endereco": self._get(row, normalized, "endereco"),
                "municipio": self._get(row, normalized, "municipio"),
                "uf": self._get(row, normalized, "uf"),
                "cep": self._get(row, normalized, "cep"),
                "telefone": self._get(row, normalized, "telefone"),
                "email": self._get(row, normalized, "email"),
                "representante": self._get(row, normalized, "representante"),
                "cpf_representante": self._get(row, normalized, "cpf_representante"),
                "rg_representante": self._get(row, normalized, "rg_representante"),
            }

        return registry

    def _get(self, row, normalized, field):
        for alias in self.ALIASES.get(field, []):
            col = normalized.get(self._norm(alias))
            if col:
                value = row.get(col, "")
                return "" if value is None else str(value).strip()
        return ""

    def _norm(self, value):
        return str(value).strip().lower()
