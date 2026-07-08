# Ajuste 3.9.1 – Acabamento Final

Objetivo:

1. Manter o nome do fornecedor na capa exatamente em CAIXA ALTA.

Exemplo:
ACÁCIA COMÉRCIO DE MEDICAMENTOS LTDA

Não converter para Title Case.

2. Continuar aplicando:
- quantidade com separador de milhar (3.570.497);
- assinatura Arial 11, negrito;
- parser universal;
- conferência financeira.

Implementação sugerida:

- Remover qualquer chamada a `.title()` ou função equivalente aplicada ao nome do fornecedor.
- Ao preencher o marcador do fornecedor na capa, utilizar:

    fornecedor_nome = fornecedor.razao_social.upper()

preservando acentos e caracteres Unicode.
