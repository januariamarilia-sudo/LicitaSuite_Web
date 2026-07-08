# LicitaSuite Web 3.8 — Parser universal e conferência financeira

Esta versão consolida dois ajustes:

## Parser universal
Aceita:
- PDF Vencedores do Processo;
- PDF Relatório de Itens Vencidos pelo Fornecedor.

Reconhece:
- fornecedor com `| Tipo:`;
- fornecedor com `- Tipo:`;
- total com `TOTAL DO VENCEDOR R$`;
- total com `Total R$`.

## Conferência financeira
- Usa o total oficial do PDF como referência.
- Confere se a soma dos itens extraídos fecha com o total oficial.
- Confere se o valor oficial aparece na ata DOCX.
- Marca em vermelho divergências na planilha.
- Não inventa valor.
- Indica correção manual quando necessário.
