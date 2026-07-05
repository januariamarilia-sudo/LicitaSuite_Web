# LicitaSuite Web 2.0 – Correção PL 53

## O que corrige

- Ignora cabeçalhos e rodapés do Portal de Compras Públicas.
- Evita criar fornecedor falso como "A autenticidade do documento...".
- Extrai fornecedor real pelo CNPJ e linha do vencedor.
- Usa o campo "Código" do PDF como número do ITEM do Apêndice.
- Usa o total do Apêndice na coluna QUANT.
- Usa descrição oficial do Apêndice.
- Remove mistura com PL antigo.
- Recria a tabela da cláusula 4 e Apêndice com base no modelo enviado no ZIP atual.
- Gera relatório de conferência.

## Como aplicar

Copie a pasta `licitasuite` desta entrega para a raiz do projeto `LicitaSuite_Web_1.0`, substituindo os arquivos existentes.

Depois rode:

```bash
git add licitasuite docs
git commit -m "LicitaSuite Web 2.0 correcao PL53"
git push
```

No Streamlit Cloud, clique em Reinício.
