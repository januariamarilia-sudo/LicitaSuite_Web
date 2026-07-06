# LicitaSuite Web 3.1.3.2 LTS — Banco em formato Mala Direta

## Correção

Compatibiliza o banco de fornecedores com planilhas usadas em mala direta.

Exemplo de ENDEREÇO aceito:

`Rodovia JK 459, KM 99 S/N Galpão, Bairro Santa Edwirges, no Município de Pouso Alegre - MG`

O sistema separa automaticamente:

- Endereço: Rodovia JK 459, KM 99 S/N Galpão, Bairro Santa Edwirges
- Município: Pouso Alegre
- UF: MG

## Também aceita

- `INSCRIÇÃO ESTAUDAL`;
- `INSCRIÇÃO ESTADUAL`;
- `ORGAO`;
- `ÓRGÃO`;
- vários e-mails no mesmo campo.

## Aplicação

```bash
git add licitasuite docs requirements.txt
git commit -m "LicitaSuite 3.1.3.2 banco mala direta"
git push
```
