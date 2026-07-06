from licitasuite.models.ata_data import AtaData, AtaItem

class CrossChecker:
    def build(self, apendice_itens, fornecedores):
        ap_by_item = {i.numero_item: i for i in apendice_itens}
        atas = []
        inconsistencias = []
        vencidos = set()

        for f in fornecedores:
            ata = AtaData(
                fornecedor_nome=f.razao_social,
                fornecedor_cnpj=f.cnpj,
                tipo=f.tipo,
                endereco=f.endereco,
                municipio=f.municipio,
                uf=f.uf,
                cep=f.cep,
                telefone=f.telefone,
                email=f.email,
                inscricao_estadual=f.inscricao_estadual,
                representante=f.representante,
                cpf_representante=f.cpf_representante,
                rg_representante=f.rg_representante,
                orgao_expedidor=f.orgao_expedidor,
            )
            for it in f.itens:
                ap = ap_by_item.get(it.numero_item)
                if not ap:
                    msg = f"Item/Lote {getattr(it,'lote', '')}/{getattr(it,'item_display', it.numero_item)} do fornecedor {f.razao_social} não localizado no Apêndice."
                    ata.inconsistencias.append(msg)
                    inconsistencias.append(msg)
                    continue
                vencidos.add(it.numero_item)
                ata.itens.append(AtaItem(
                    numero_item=it.numero_item,
                    codigo_siplan=ap.codigo_siplan,
                    descricao_oficial=ap.descricao,
                    apresentacao=ap.apresentacao,
                    marca=it.marca,
                    fabricante=it.fabricante,
                    modelo=it.modelo,
                    quantidade=ap.total or it.quantidade_pdf,
                    valor_unitario=it.valor_unitario,
                    valor_total=it.valor_total,
                    appendix_cells_text=ap.cells_text,
                    lote=getattr(ap, 'lote', None),
                    item_display=getattr(ap, 'item_display', None) or getattr(it, 'item_display', None),
                    lote_display=getattr(ap, 'lote_display', None),
                ))
            if ata.itens:
                atas.append(ata)

        return {
            "atas": atas,
            "itens_sem_vencedor": sorted(set(ap_by_item.keys()) - vencidos),
            "inconsistencias": inconsistencias
        }
