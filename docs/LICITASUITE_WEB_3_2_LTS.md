# LicitaSuite Web 3.2 LTS — Parser confiável e geração com pendências

Esta versão consolida:

- leitura por blocos de fornecedor;
- CNPJ quebrado;
- itens apenas após o cabeçalho da tabela;
- telefone, CEP e endereço não são lidos como item;
- parada no TOTAL DO VENCEDOR;
- uso do TOTAL DO VENCEDOR como validação oficial;
- fornecedor com item único recebe o total oficial;
- geração segue com pendências registradas;
- não inventa valores: se não detectar, marca para conferência manual.
