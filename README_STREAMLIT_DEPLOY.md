# LicitaSuite Web 1.0 — Deploy no Streamlit Community Cloud

## Objetivo

Publicar o LicitaSuite Web gratuitamente no Streamlit Community Cloud.

## Estrutura esperada no GitHub

A raiz do repositório deve conter:

```text
LicitaSuite_Web_1_0
├── web
│   ├── app.py
│   ├── requirements_web.txt
│   └── ...
├── licitasuite
├── config
├── docs
├── requirements.txt
├── .streamlit
│   └── config.toml
└── README_STREAMLIT_DEPLOY.md
```

## Arquivo principal para o Streamlit

No Streamlit Cloud, informe:

```text
web/app.py
```

## Passo a passo

1. Crie uma conta no GitHub.
2. Crie um repositório privado chamado `LicitaSuite_Web_1_0`.
3. Envie a pasta do LicitaSuite Web para esse repositório.
4. Acesse o Streamlit Community Cloud.
5. Clique em **New app**.
6. Escolha o repositório `LicitaSuite_Web_1_0`.
7. Em **Main file path**, coloque `web/app.py`.
8. Clique em **Deploy**.

## Observações importantes

- O Streamlit Cloud instala as dependências pelo `requirements.txt` da raiz.
- O app deve encontrar a pasta `licitasuite` na raiz do repositório.
- Não envie arquivos de processos reais para o GitHub.
- Não envie documentos sigilosos.
- Use repositório privado.

## Limitações da versão gratuita

- O app pode “dormir” após ficar sem uso.
- O primeiro acesso pode demorar mais.
- O limite de memória é adequado para testes e uso leve.
- Para documentos sensíveis, use com cuidado e evite deixar arquivos salvos permanentemente.

## Próximo ajuste recomendado

Depois que subir no Streamlit, adicionar:
- senha simples de acesso;
- limpeza automática de uploads;
- aviso de confidencialidade.