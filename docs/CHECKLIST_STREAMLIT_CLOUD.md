# Checklist — Publicação no Streamlit Cloud

## Antes de subir

- [ ] Fazer backup da versão desktop 6.1 LTS.
- [ ] Criar cópia separada `LicitaSuite_Web_1_0`.
- [ ] Confirmar que `web/app.py` roda localmente.
- [ ] Confirmar que o motor gera atas pela web local.
- [ ] Remover arquivos reais de licitação antes de subir para GitHub.
- [ ] Remover pastas `output`, `temp`, `logs`, `web_uploads`.

## No GitHub

- [ ] Criar repositório privado.
- [ ] Subir `web/app.py`.
- [ ] Subir pasta `licitasuite`.
- [ ] Subir `requirements.txt`.
- [ ] Subir `.streamlit/config.toml`.

## No Streamlit

- [ ] Conectar conta GitHub.
- [ ] Escolher repositório.
- [ ] Definir main file: `web/app.py`.
- [ ] Clicar em Deploy.
- [ ] Testar upload de ZIP fictício ou processo teste.

## Depois de publicar

- [ ] Testar com um processo real.
- [ ] Baixar o ZIP gerado.
- [ ] Conferir as atas.
- [ ] Testar em outro computador.
- [ ] Adicionar senha de acesso.