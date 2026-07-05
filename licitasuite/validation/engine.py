from dataclasses import dataclass, field

@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors

class ValidationEngine:
    def validate(self, cross_result):
        result = ValidationResult()

        for ata in cross_result["atas"]:
            if not ata.fornecedor_nome:
                result.errors.append("Fornecedor sem nome.")
            if not ata.fornecedor_cnpj:
                result.warnings.append(f"Fornecedor {ata.fornecedor_nome} sem CNPJ.")
            if not ata.itens:
                result.warnings.append(f"Fornecedor {ata.fornecedor_nome} sem itens.")

            seen = set()
            for item in ata.itens:
                if item.numero_item in seen:
                    result.errors.append(f"Item {item.numero_item} duplicado para {ata.fornecedor_nome}.")
                seen.add(item.numero_item)

                if not item.descricao_oficial:
                    result.errors.append(f"Item {item.numero_item} sem descrição oficial.")
                if item.valor_total < 0:
                    result.errors.append(f"Item {item.numero_item} com valor negativo.")

        for inc in cross_result["inconsistencias_gerais"]:
            result.errors.append(inc)

        for item in cross_result["itens_sem_vencedor"]:
            result.warnings.append(f"Item {item} do Apêndice sem vencedor identificado.")

        return result
