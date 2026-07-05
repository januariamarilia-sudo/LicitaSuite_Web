class SupplierRegistryService:
    """
    Associa dados cadastrais aos fornecedores identificados no PDF usando CNPJ.
    """

    def enrich(self, fornecedores, registry_by_cnpj):
        for fornecedor in fornecedores:
            key = self._only_digits(fornecedor.cnpj)
            registry = registry_by_cnpj.get(key)

            if not registry:
                continue

            fornecedor.razao_social = registry.razao_social or fornecedor.razao_social
            fornecedor.endereco = registry.endereco
            fornecedor.municipio = registry.municipio
            fornecedor.uf = registry.uf
            fornecedor.cep = registry.cep
            fornecedor.telefone = registry.telefone
            fornecedor.email = registry.email

            # Campos adicionais são anexados dinamicamente para evitar quebrar versões anteriores.
            fornecedor.representante = registry.representante
            fornecedor.cpf_representante = registry.cpf_representante
            fornecedor.rg_representante = registry.rg_representante

        return fornecedores

    def _only_digits(self, value):
        return "".join(ch for ch in str(value or "") if ch.isdigit())
