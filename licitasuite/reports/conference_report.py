from pathlib import Path
import json
from licitasuite.parsers.text_utils import format_money

class ConferenceReport:
    def write(self, result):
        out = Path("output/relatorio_conferencia.txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["RELATÓRIO DE CONFERÊNCIA - LICITASUITE 3.0", ""]
        for ata in result["atas"]:
            lines.append(f"Fornecedor: {ata.fornecedor_nome}")
            lines.append(f"CNPJ: {ata.fornecedor_cnpj}")
            lines.append(f"Itens: {len(ata.itens)}")
            lines.append(f"Valor total: {format_money(ata.valor_total, 2)}")
            lines.append("Itens: " + ", ".join(str(i.numero_item) for i in ata.itens))
            if ata.inconsistencias:
                lines.append("Inconsistências: " + " | ".join(ata.inconsistencias))
            lines.append("")
        if result.get("itens_sem_vencedor"):
            lines.append("Itens do Apêndice sem vencedor: " + ", ".join(map(str, result["itens_sem_vencedor"])))
        if result.get("inconsistencias"):
            lines.append("Inconsistências gerais: " + " | ".join(result["inconsistencias"]))
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
                    "itens": [i.numero_item for i in ata.itens],
                    "valor_total": ata.valor_total,
                    "inconsistencias": ata.inconsistencias,
                }
                for ata in result["atas"]
            ],
            "itens_sem_vencedor": result.get("itens_sem_vencedor", []),
            "inconsistencias": result.get("inconsistencias", []),
        }
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return out
