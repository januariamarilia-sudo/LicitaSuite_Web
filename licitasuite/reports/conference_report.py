from pathlib import Path
import json
from licitasuite.parsers.text_utils import format_money

class ConferenceReport:
    def write(self, result):
        out = Path("output/relatorio_conferencia.txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["RELATÓRIO DE CONFERÊNCIA - LICITASUITE WEB 3.1.3 LTS", ""]

        for ata in result["atas"]:
            lines.append(f"Fornecedor: {ata.fornecedor_nome}")
            lines.append(f"CNPJ: {ata.fornecedor_cnpj}")
            lines.append(f"Endereço: {getattr(ata, 'endereco', '')}")
            lines.append(f"CEP: {getattr(ata, 'cep', '')}")
            lines.append(f"Telefone: {getattr(ata, 'telefone', '')}")
            lines.append(f"E-mail: {getattr(ata, 'email', '')}")
            lines.append(f"Inscrição Estadual: {getattr(ata, 'inscricao_estadual', '')}")
            lines.append(f"Representante: {getattr(ata, 'representante', '')}")
            lines.append(f"CPF: {getattr(ata, 'cpf_representante', '')}")
            lines.append(f"RG: {getattr(ata, 'rg_representante', '')}")
            lines.append(f"Órgão expedidor: {getattr(ata, 'orgao_expedidor', '')}")
            lines.append(f"Itens: {len(ata.itens)}")
            lines.append(f"Valor total: {format_money(ata.valor_total, 2)}")
            lines.append("Itens: " + ", ".join(str(i.numero_item) for i in ata.itens))
            if ata.inconsistencias:
                lines.append("Observações/Inconsistências: " + " | ".join(ata.inconsistencias))
            lines.append("")

        if result.get("itens_sem_vencedor"):
            lines.append("Itens do Apêndice sem vencedor: " + ", ".join(map(str, result["itens_sem_vencedor"])))
        if result.get("inconsistencias"):
            lines.append("Observações gerais: " + " | ".join(result["inconsistencias"]))

        out.write_text("\n".join(lines), encoding="utf-8")
        return out

    def write_json(self, result):
        out = Path("output/relatorio_conferencia.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "fornecedores": [
                {
                    "nome": ata.fornecedor_nome,
                    "cnpj": ata.fornecedor_cnpj,
                    "endereco": getattr(ata, "endereco", ""),
                    "cep": getattr(ata, "cep", ""),
                    "telefone": getattr(ata, "telefone", ""),
                    "email": getattr(ata, "email", ""),
                    "inscricao_estadual": getattr(ata, "inscricao_estadual", ""),
                    "representante": getattr(ata, "representante", ""),
                    "cpf": getattr(ata, "cpf_representante", ""),
                    "rg": getattr(ata, "rg_representante", ""),
                    "orgao_expedidor": getattr(ata, "orgao_expedidor", ""),
                    "itens": [i.numero_item for i in ata.itens],
                    "valor_total": ata.valor_total,
                    "observacoes": ata.inconsistencias,
                }
                for ata in result["atas"]
            ],
            "itens_sem_vencedor": result.get("itens_sem_vencedor", []),
            "observacoes_gerais": result.get("inconsistencias", []),
        }
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return out
