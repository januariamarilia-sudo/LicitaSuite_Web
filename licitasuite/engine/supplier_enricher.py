from licitasuite.utils.formatters import only_digits

class SupplierEnricher:
    def enrich(self, fornecedores, registry):
        for fornecedor in fornecedores:
            data = registry.get(only_digits(fornecedor.cnpj))
            if not data:
                continue

            fornecedor.razao_social = data.get("razao_social") or fornecedor.razao_social
            fornecedor.endereco = data.get("endereco", "")
            fornecedor.municipio = data.get("municipio", "")
            fornecedor.uf = data.get("uf", "")
            fornecedor.cep = data.get("cep", "")
            fornecedor.telefone = data.get("telefone", "")
            fornecedor.email = data.get("email", "")
            fornecedor.representante = data.get("representante", "")
            fornecedor.cpf_representante = data.get("cpf_representante", "")
            fornecedor.rg_representante = data.get("rg_representante", "")

        return fornecedores
