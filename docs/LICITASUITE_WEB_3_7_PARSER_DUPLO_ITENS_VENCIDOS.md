# LicitaSuite Web 3.7 — Parser duplo para PDF de vencedores

Esta versão adapta o parser para aceitar dois tipos de PDF:

1. Vencedores do Processo
- Usa fornecedor com `| Tipo:`
- Usa total com `TOTAL DO VENCEDOR R$`

2. Relatório de Itens Vencidos pelo Fornecedor
- Usa fornecedor com `- Tipo:`
- Usa total com `Total R$`

Objetivo:
- Permitir usar o PDF de itens vencidos quando ele vier com valores mais limpos.
- Manter compatibilidade com o PDF antigo.
- Continuar sem inventar valores.
