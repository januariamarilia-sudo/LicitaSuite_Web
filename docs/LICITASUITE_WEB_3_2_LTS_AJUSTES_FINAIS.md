# LicitaSuite Web 3.2 LTS — Ajustes Finais

## Inclui correções preventivas

- Assinatura:
  - atualiza a célula do fornecedor no bloco final;
  - nome da empresa em padrão legível;
  - representante ausente fica como `[INFORMAÇÃO NÃO LOCALIZADA]`.

- Dados do fornecedor:
  - limpa resíduos do Portal de Compras;
  - não inventa dados;
  - preserva campos ausentes com marcador.

- Largura/altura:
  - preserva colunas do modelo;
  - clona linha do modelo;
  - linha de total compacta;
  - linhas de item automáticas para não cortar descrição.

- Apêndice:
  - preserva estrutura do modelo;
  - usa `appendix_cells_text`;
  - mantém quantitativos originais do Apêndice.

- Nome do arquivo:
  - remove resíduos;
  - padrão `ATA DE REGISTRO DE PREÇOS - FORNECEDOR.docx`.

## Aplicação

```bash
git add licitasuite docs
git commit -m "LicitaSuite Web 3.2 LTS ajustes finais"
git push
```

Depois clicar em **Reinício** no Streamlit.
