# LicitaSuite Web 3.1.4 LTS — Processo por Lote

Correção para processos em que o Apêndice e o PDF trabalham por **LOTE + ITEM**, e não por Código SIPLAN.

## O que corrige

- Apêndice com colunas `LOTE`, `ITEM`, `DESCRITIVO`, `APRESENTAÇÃO`.
- PDF de vencedores com blocos `LoteXX` e item `0001`.
- Tabela da ata com cabeçalho `LOTE`, `ITEM`, `QUANT.`, `DESCRIÇÃO`.
- Mantém compatibilidade com processos por Código SIPLAN.
- Continua aceitando banco de fornecedores `.xlsx`.

## Aplicação

```bash
git add licitasuite docs requirements.txt
git commit -m "LicitaSuite Web 3.1.4 processo por lote"
git push
```
