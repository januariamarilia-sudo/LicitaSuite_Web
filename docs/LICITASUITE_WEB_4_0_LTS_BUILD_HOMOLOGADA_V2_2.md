# LicitaSuite Web 4.0 LTS — Build Homologada v2.2

Correção pontual:

- A formatação homologada passa a ler diretamente o BANCO DE DADOS GERAL.xlsx.
- O preâmbulo busca CPF, RG, ORGAO, ENDEREÇO, CEP, FONE, EMAIL, CNPJ, Inscrição Estadual e Representante diretamente na planilha.
- Suporta dados mascarados com asterisco, como ***.***.***-68 e ******-9.
- Corrige o caso em que o SupplierDatabase enriquecia parte dos dados, mas não repassava CPF/RG/ORGAO para a ata.

O restante permanece igual à v2.1.
