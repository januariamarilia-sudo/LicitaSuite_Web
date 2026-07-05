# LicitaSuite 3.0 Web Engine

## Objetivo

Motor novo para novos PLs, com isolamento por processo e geração baseada no modelo enviado.

## Principais mudanças

- Usa exclusivamente o DOCX enviado no ZIP atual.
- Detecta modelo, Apêndice e PDF por conteúdo.
- Parser de vencedores ignora cabeçalhos e rodapés.
- O código do PDF é tratado como número do ITEM.
- O cruzamento é feito com a coluna ITEM do Apêndice.
- A descrição oficial vem do Apêndice.
- Geração por cópia do modelo e substituição localizada.
- Relatório de conferência em TXT e JSON.

## Como aplicar

Copie a pasta `licitasuite` para a raiz do projeto `LicitaSuite_Web_1.0`, substituindo os arquivos.

Depois:

```bash
git add licitasuite docs
git commit -m "LicitaSuite 3.0 Web Engine"
git push
```

No Streamlit Cloud, clique em Reinício.
