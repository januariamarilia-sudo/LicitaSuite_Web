# LicitaSuite Web 3.1.3 LTS — Banco de Fornecedores

Inclui leitura opcional de planilha `.xlsx` dentro do ZIP do processo.

## Como usar

Coloque no mesmo ZIP:

- modelo da ata `.docx`;
- apêndice `.docx`;
- PDF dos vencedores `.pdf`;
- banco de fornecedores `.xlsx`.

O sistema identifica a planilha automaticamente quando o nome contém:
- banco;
- fornecedor;
- dados.

## Campos lidos

- FORNECEDOR;
- ENDEREÇO;
- CEP;
- FONE;
- EMAIL;
- CNPJ;
- INSCRIÇÃO ESTADUAL;
- REPRESENTANTE;
- CPF;
- RG;
- ÓRGÃO.

## Regras

1. Procura primeiro por CNPJ.
2. Se não localizar, procura por nome.
3. Se não encontrar, mantém `[INFORMAÇÃO NÃO LOCALIZADA]`.
4. Se houver duplicidade, gera observação no relatório e não interrompe as atas.
