# LicitaSuite 2.3 — Valores fidedignos do PDF

Correção do parser do PDF de vencedores para:
- capturar 24 fornecedores;
- aceitar CNPJ quebrado em duas linhas;
- capturar valor total de item mesmo quando o PDF quebra o valor após `R$`;
- comparar a soma dos itens com o `TOTAL DO VENCEDOR`;
- não inventar valores;
- quando valor não for detectado, deixar o item com valor 0 e marcar `VALOR_TOTAL_NAO_DETECTADO_MANUALMENTE` na origem para conferência.

Após aplicar, teste novamente com o PL 48.2026 PE 37.2026.
