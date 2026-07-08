# LicitaSuite Web 3.6 — Conferência financeira oficial

Esta versão altera a lógica da conferência automática:

- O valor oficial passa a ser o `TOTAL DO VENCEDOR R$` do PDF.
- O relatório confronta:
  1. TOTAL DO VENCEDOR do PDF;
  2. soma dos itens lidos no PDF;
  3. presença desse total na ata DOCX.

Regras:
- Se a soma dos itens não fechar com o TOTAL DO VENCEDOR, marca vermelho.
- Se o TOTAL DO VENCEDOR não aparecer na ata, marca vermelho.
- O sistema não inventa valor.
- O campo de observação indica correção manual necessária.
