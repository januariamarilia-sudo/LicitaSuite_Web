# LicitaSuite Web 3.1 LTS

## Correções

1. Quantitativos:
   - `27.030` agora vira `27030`;
   - evita `27,03`.

2. Valores:
   - preço unitário fica na coluna correta;
   - preço total fica na coluna correta;
   - compatível com modelos com ou sem coluna `MODELO`.

3. Tabela:
   - identifica colunas pelo cabeçalho real do modelo;
   - não depende de posição fixa;
   - preserva linhas clonadas.

4. Descrição:
   - primeira parte até `" - "` em negrito;
   - restante em fonte normal;
   - Arial 8.

5. Valor total:
   - linha `VALOR TOTAL:` permanece mesclada;
   - valor vai para a última coluna correta.

## Aplicação

Copiar a pasta `licitasuite` para a raiz do projeto, substituir arquivos e executar:

```bash
git add licitasuite docs
git commit -m "LicitaSuite Web 3.1 LTS"
git push
```

Depois clicar em **Reinício** no Streamlit.
