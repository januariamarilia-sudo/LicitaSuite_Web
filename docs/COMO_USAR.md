# Como usar o LicitaSuite v4.0 Produção

1. Abra o VS Code na pasta do projeto.
2. Execute:

```powershell
python main.py
```

3. Clique em **Selecionar ZIP do processo**.
4. Escolha o ZIP contendo:
   - Modelo da Ata;
   - Apêndice;
   - PDF dos vencedores;
   - planilha de fornecedores, se houver.
5. Clique em **Gerar Atas**.
6. Verifique a pasta:

`output/atas_geradas`

## Resultado

O sistema gerará:
- DOCX por fornecedor;
- ZIP final;
- relatório de conferência;
- JSON dos dados.
