from copy import deepcopy
from licitasuite.models.ata_data import AtaData
from licitasuite.models.ata_item import AtaItem

class CrossChecker:
    def build_atas(self, apendice_itens, fornecedores):
        ap_by_item = {i.numero_item: i for i in apendice_itens}
        item_to_supplier = {}
        atas = []

        for fornecedor in fornecedores:
            ata = AtaData(
                fornecedor_nome=fornecedor.razao_social,
                fornecedor_cnpj=fornecedor.cnpj,
                endereco=getattr(fornecedor, "endereco", ""),
                municipio=getattr(fornecedor, "municipio", ""),
                uf=getattr(fornecedor, "uf", ""),
                cep=getattr(fornecedor, "cep", ""),
                telefone=getattr(fornecedor, "telefone", ""),
                email=getattr(fornecedor, "email", ""),
                representante=getattr(fornecedor, "representante", ""),
                cpf_representante=getattr(fornecedor, "cpf_representante", ""),
                rg_representante=getattr(fornecedor, "rg_representante", ""),
            )

            for pdf_item in fornecedor.itens:
                ap_item = ap_by_item.get(pdf_item.numero_item)
                if not ap_item:
                    ata.inconsistencias.append(
                        f"ITEM {pdf_item.numero_item} consta no PDF, mas não foi localizado no Apêndice."
                    )
                    continue

                item_to_supplier.setdefault(pdf_item.numero_item, []).append(fornecedor.razao_social)

                # A quantidade que deve aparecer na Ata é a do Apêndice.
                quantidade = ap_item.total if ap_item.total else pdf_item.quantidade

                ata.itens.append(AtaItem(
                    numero_item=pdf_item.numero_item,
                    codigo_siplan=ap_item.codigo_siplan,
                    descricao_oficial=ap_item.descricao,
                    apresentacao=ap_item.apresentacao,
                    marca=pdf_item.marca,
                    fabricante=pdf_item.fabricante,
                    modelo=pdf_item.modelo,
                    quantidade=quantidade,
                    valor_unitario=pdf_item.valor_unitario,
                    valor_total=pdf_item.valor_total,
                    appendix_cells_text=list(getattr(ap_item, "cells_text", [])),
                    appendix_row_xml=deepcopy(getattr(ap_item, "raw_row_xml", None)),
                ))

            atas.append(ata)

        itens_ap = set(ap_by_item.keys())
        itens_vencidos = set(item_to_supplier.keys())
        duplicados = {k: v for k, v in item_to_supplier.items() if len(v) > 1}

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
