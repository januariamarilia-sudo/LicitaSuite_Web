# LicitaSuite Web 3.4 — Correção de valores quebrados no PDF

Esta versão corrige a leitura de valores totais quando o PDF quebra o valor em outra linha.

Exemplo problemático:
0003 ... CPR R$ 0,5817 R$
500MG ... 2.076.958,1049

Antes:
- O sistema lia apenas o valor unitário ou ignorava o total.

Agora:
- O parser identifica a quantidade/unidade.
- Captura o valor unitário.
- Busca o próximo valor financeiro como valor total, mesmo se estiver sem `R$` na continuação da linha.

Objetivo:
- Corrigir valores de fornecedores com múltiplos itens, como Acácia, BH Farma, Cristália, Medilar, Multifarma e Zion.
- Corrigir fornecedor VIVA no PL 53 quando o total foi quebrado.
- Não inventar valor: se não houver valor numérico confiável, mantém marcação para conferência manual.
