from licitasuite.models.ata_data import AtaData
from licitasuite.models.ata_item import AtaItem

class CrossChecker:
    def build_atas(self, apendice_itens, fornecedores):
        ap_by_item = {item.numero_item: item for item in apendice_itens}
        item_to_suppliers = {}
        atas = []

        for fornecedor in fornecedores:
            ata = AtaData(
                fornecedor_nome=fornecedor.razao_social,
                fornecedor_cnpj=fornecedor.cnpj,
                tipo=getattr(fornecedor, "tipo", ""),
                endereco=getattr(fornecedor, "endereco", ""),
                municipio=getattr(fornecedor, "municipio", ""),
                uf=getattr(fornecedor, "uf", ""),
                cep=getattr(fornecedor, "cep", ""),
                telefone=getattr(fornecedor, "telefone", ""),
                email=getattr(fornecedor, "email", ""),
                inscricao_estadual=getattr(fornecedor, "inscricao_estadual", ""),
                representante=getattr(fornecedor, "representante", ""),
                cpf_representante=getattr(fornecedor, "cpf_representante", ""),
                rg_representante=getattr(fornecedor, "rg_representante", ""),
                orgao_expedidor=getattr(fornecedor, "orgao_expedidor", ""),
            )

            for pdf_item in fornecedor.itens:
                ap_item = ap_by_item.get(pdf_item.numero_item)
                if not ap_item:
                    ata.inconsistencias.append(
                        f"ITEM {pdf_item.numero_item} consta no PDF, mas não foi localizado na coluna ITEM do Apêndice."
                    )
                    continue

                item_to_suppliers.setdefault(pdf_item.numero_item, []).append(fornecedor.razao_social)

                ata.itens.append(AtaItem(
                    numero_item=pdf_item.numero_item,
                    codigo_siplan=ap_item.codigo_siplan,
                    descricao_oficial=ap_item.descricao,
                    apresentacao=ap_item.apresentacao,
                    marca=pdf_item.marca,
                    fabricante=pdf_item.fabricante,
                    modelo=pdf_item.modelo,
                    quantidade=ap_item.total or pdf_item.quantidade,
                    valor_unitario=pdf_item.valor_unitario,
                    valor_total=pdf_item.valor_total,
                    appendix_cells_text=list(getattr(ap_item, "cells_text", [])),
                ))

            atas.append(ata)

        itens_ap = set(ap_by_item.keys())
        itens_vencidos = set(item_to_suppliers.keys())
        duplicados = {k: v for k, v in item_to_suppliers.items() if len(v) > 1}

        return {
            "atas": atas,
            "itens_vencidos": sorted(itens_vencidos),
            "itens_sem_vencedor": sorted(itens_ap - itens_vencidos),
            "duplicados": duplicados,
            "inconsistencias_gerais": [
                f"ITEM {item} aparece para mais de um fornecedor: {', '.join(suppliers)}"
                for item, suppliers in duplicados.items()
            ],
        }
