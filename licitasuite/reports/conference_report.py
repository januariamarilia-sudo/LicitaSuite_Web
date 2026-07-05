from pathlib import Path
import json
from licitasuite.utils.formatters import format_brl

class ConferenceReport:
    def write(self, cross_result, validation_result, output_path="output/relatorio_conferencia.txt"):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = ["RELATÓRIO DE CONFERÊNCIA — LICITASUITE", ""]
        lines.append(f"Fornecedores processados: {len(cross_result['atas'])}")
        lines.append(f"Itens vencidos identificados: {len(cross_result['itens_vencidos'])}")
        lines.append(f"Itens sem vencedor identificado: {len(cross_result['itens_sem_vencedor'])}")
        lines.append("")

        if validation_result.errors:
            lines.append("ERROS:")
            for err in validation_result.errors:
                lines.append(f"- {err}")
            lines.append("")

        if validation_result.warnings:
            lines.append("ALERTAS:")
            for warn in validation_result.warnings:
                lines.append(f"- {warn}")
            lines.append("")

        for ata in cross_result["atas"]:
            lines.append("=" * 70)
            lines.append(f"Fornecedor: {ata.fornecedor_nome}")
            lines.append(f"CNPJ: {ata.fornecedor_cnpj}")
            lines.append(f"Itens: {len(ata.itens)}")
            lines.append(f"Valor total: {format_brl(ata.valor_total, 2)}")
            lines.append("")

            for item in ata.itens:
                lines.append(f"ITEM {item.numero_item} | SIPLAN {item.codigo_siplan} | Total {format_brl(item.valor_total, 2)}")
                lines.append(f"Descrição: {item.descricao_oficial[:350]}")
                lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    def write_json(self, cross_result, validation_result, output_path="output/dados_para_atas.json"):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "validation": {
                "ok": validation_result.ok,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
            },
            "itens_vencidos": cross_result["itens_vencidos"],
            "itens_sem_vencedor": cross_result["itens_sem_vencedor"],
            "inconsistencias_gerais": cross_result["inconsistencias_gerais"],
            "fornecedores": [],
        }

        for ata in cross_result["atas"]:
            data["fornecedores"].append({
                "nome": ata.fornecedor_nome,
                "cnpj": ata.fornecedor_cnpj,
                "endereco": ata.endereco,
                "municipio": ata.municipio,
                "uf": ata.uf,
                "cep": ata.cep,
                "telefone": ata.telefone,
                "email": ata.email,
                "representante": ata.representante,
                "cpf_representante": ata.cpf_representante,
                "rg_representante": ata.rg_representante,
                "valor_total": ata.valor_total,
                "inconsistencias": ata.inconsistencias,
                "itens": [
                    {
                        "numero_item": item.numero_item,
                        "codigo_siplan": item.codigo_siplan,
                        "descricao_oficial": item.descricao_oficial,
                        "apresentacao": item.apresentacao,
                        "marca": item.marca,
                        "fabricante": item.fabricante,
                        "modelo": item.modelo,
                        "quantidade": item.quantidade,
                        "valor_unitario": item.valor_unitario,
                        "valor_total": item.valor_total,
                        "appendix_cells_text": item.appendix_cells_text,
                    }
                    for item in ata.itens
                ],
            })

        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path
