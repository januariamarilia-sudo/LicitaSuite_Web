# Módulo Opcional de Mala Direta de Fornecedores

Este módulo foi criado para ser seguro.

Ele não altera:
- tabelas;
- itens;
- valores;
- apêndice;
- cláusula 4;
- formatação das atas.

## O que ele faz

Se existir uma planilha `.xlsx` no ZIP do processo, ele pode preencher dados cadastrais:

- endereço;
- município;
- UF;
- CEP;
- telefone;
- e-mail;
- inscrição estadual;
- representante;
- CPF;
- RG;
- órgão expedidor.

## Exemplo aceito

`Rodovia JK 459, KM 99 S/N Galpão, Bairro Santa Edwirges, no Município de Pouso Alegre - MG`

O sistema separa:
- endereço;
- município;
- UF.

## Uso técnico

```python
from licitasuite.extensoes.mala_direta_fornecedores import BancoMalaDiretaFornecedores

banco = BancoMalaDiretaFornecedores.localizar_no_diretorio(pasta_extraida)

for ata in atas:
    banco.enriquecer_ata_data(ata)
```
