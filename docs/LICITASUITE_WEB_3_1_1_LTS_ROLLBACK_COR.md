# LicitaSuite Web 3.1.1 LTS — Rollback + Cor

## Objetivo

Esta versão desfaz a 3.2, que mexeu demais em largura, altura e estrutura da tabela.

Ela volta para a base 3.1 LTS, que estava mais próxima do resultado correto, mantendo:

- quantitativo corrigido;
- valores nas colunas corretas;
- compatibilidade com modelo com ou sem coluna MODELO;
- linha VALOR TOTAL horizontal;
- descrição com negrito controlado;
- preservação da cor do modelo por clonagem das linhas.

## O que NÃO faz

- não força largura de tabela;
- não força altura das linhas de item;
- não altera o layout global;
- não mexe na cor do cabeçalho;
- não recria tabela do zero fora da linha clonada do modelo.

## Aplicação

Copie a pasta `licitasuite` para a raiz do projeto e substitua os arquivos.

Depois execute:

```bash
git add licitasuite docs
git commit -m "Rollback 3.1.1 LTS cor"
git push
```

Depois clique em **Reinício** no Streamlit.