# LicitaSuite Web 3.1.3.1 LTS — Correção de Requirements

## Correção

A versão 3.1.3 do banco de fornecedores estava com `requirements.txt` incompleto.

Faltava principalmente:

- python-docx

Sem isso, o Streamlit Cloud exibia:

`No module named 'docx'`

## Dependências corrigidas

- streamlit
- python-docx
- pdfplumber
- openpyxl
- num2words

## Aplicação

Copiar `requirements.txt` junto com `licitasuite` e `docs`.

Depois executar:

```bash
git add licitasuite docs requirements.txt
git commit -m "LicitaSuite 3.1.3.1 corrige requirements"
git push
```

Depois clicar em **Reinício** no Streamlit.