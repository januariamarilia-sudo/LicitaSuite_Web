# LicitaSuite v6.0 Estável (LTS)

Versão oficial estável do LicitaSuite para geração de Atas de Registro de Preços.

## Finalidade

O LicitaSuite v6.0 Estável é destinado exclusivamente à geração de Atas de Registro de Preços por fornecedor, a partir dos documentos de cada processo.

## Escopo da versão

Esta versão gera:

- uma Ata DOCX para cada fornecedor vencedor;
- ZIP final com todas as Atas;
- relatório de conferência;
- dados auxiliares para validação.

## Entrada esperada

O usuário deve selecionar um ZIP do processo contendo, preferencialmente:

1. Modelo da Ata em DOCX;
2. Apêndice em DOCX;
3. PDF dos vencedores;
4. Planilha de fornecedores, quando houver.

## Regras principais

- Usa sempre o modelo de Ata enviado no próprio processo.
- Não usa modelo fixo.
- Preserva a estrutura e a formatação do modelo.
- Usa a descrição oficial do Apêndice.
- Usa os quantitativos do Apêndice.
- Separa os itens por fornecedor.
- Gera uma Ata por fornecedor.
- Não inventa dados cadastrais.
- Campos sem informação ficam em branco/destacados para preenchimento manual.
- Mantém o Apêndice com a formatação original sempre que possível.
- Mantém a tabela da cláusula 4 no padrão definido durante a homologação.
- Mantém a linha VALOR TOTAL compacta, mesclada e horizontal.

## Política LTS

A partir desta versão, o LicitaSuite entra em modo estável.

Não serão adicionadas novas funcionalidades nesta linha.

Serão aceitas apenas:

- correções de bugs;
- ajustes finos de layout;
- compatibilidade com novos modelos de Ata;
- correções pontuais de leitura de PDFs ou Apêndices diferentes.

## Como aplicar no projeto atual

Copie a pasta `licitasuite` desta entrega para dentro do projeto atual:

`C:\Users\janua\OneDrive\Documentos\LicitaSuite`

Substitua os arquivos existentes.

Depois execute:

```powershell
python main.py
```

## Próxima etapa recomendada

Após validar esta versão em processos reais, gerar o executável/instalador para uso diário sem VS Code e sem terminal.