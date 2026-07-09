# Contexto integrado — Licita Suite-JM.adm e FOCO DOCS

Este documento incorpora integralmente as ideias, decisões e entregas
descritas na conversa de origem do FOCO DOCS.

## Ponto de partida

O protótipo inicial era um HTML local, aberto diretamente no navegador e com
dados salvos em LocalStorage. A conversa concluiu que as rotinas envolvidas
mereciam um sistema profissional e modular.

Rotinas citadas:

- geração de Atas de Registro de Preços;
- organização de documentos de credenciamento;
- conferência de habilitação;
- união, divisão, numeração e compressão de PDFs;
- separação e geração de ZIPs;
- controle de vencimentos;
- biblioteca de prompts;
- pesquisas de preços e relatórios;
- controle de prazos, publicações, extratos e SICOM;
- cadastro, certidões e histórico de fornecedores.

Como o módulo ARP já existia, definiu-se um produto separado chamado
**FOCO DOCS — Organizador de Documentos de Fornecedores**, posteriormente
integrado ao portal modular Licita Suite-JM.adm.

## Escopo funcional integral

### Organizador de documentos

- importar ZIP;
- identificar e separar documentos básicos e técnicos;
- destinar documentos não classificados para uma pasta própria;
- renomear arquivos segundo padrão;
- gerar um novo ZIP organizado;
- processar tudo por um fluxo de um clique.

### Habilitação e credenciamento

- checklist por fornecedor, item ou lote;
- identificação de documentos faltantes, vencidos e substituíveis;
- perfis Genérico, Laboratório, Ambulância e Medicamentos;
- parecer preliminar;
- score documental;
- histórico e auditoria.

### Inteligência documental

- OCR para PDFs escaneados;
- OCR para imagens JPG, PNG e TIFF;
- identificação de PDF sem camada de texto;
- extração de CNPJ, validade e tipo de documento;
- cache de OCR;
- processamento paralelo;
- logs claros e recuperação de erro;
- relatório de inteligência documental.

### Experiência de uso

- PWA instalável;
- estrutura offline com Service Worker;
- configurações persistentes;
- histórico local;
- drag-and-drop;
- botões grandes;
- barra de progresso detalhada;
- poucos campos e reaproveitamento das últimas configurações.

### Integrações e automação

- consultas públicas, quando técnica e juridicamente permitidas;
- Receita Federal, TCU, FGTS e CNDT;
- geração e organização automática de comprovantes;
- atualização de documentos recorrentes;
- reutilização de documentos válidos de fornecedores.

### Relatórios e gestão

- relatórios profissionais em PDF e Excel;
- checklist oficial;
- ata de conferência;
- painel administrativo;
- estatísticas e dashboard;
- backup, importação e exportação;
- fluxos de credenciamento, pregão e SRP.

## Roteiro consolidado

### Mega Sprint 6

Equivale às Sprints 6, 7 e 8:

- PWA e funcionamento offline;
- configurações e histórico locais;
- drag-and-drop;
- OCR e detecção de documentos sem texto;
- perfis documentais;
- cache, processamento paralelo e logs;
- modo Um Clique;
- relatório documental, checklist e ZIP organizado.

### Mega Sprint 7

Equivale às Sprints 9, 10 e 11:

- motor de regras da habilitação;
- parecer automático;
- checklist inteligente;
- relatórios PDF e Excel;
- banco de fornecedores;
- pesquisa por CNPJ e razão social;
- favoritos, reutilização, score e auditoria.

### Mega Sprint 8

Equivale às Sprints 12 a 15:

- IA para reconhecimento amplo de documentos;
- renovação e atualização automática;
- fluxos de credenciamento, pregão e SRP;
- controle de validade;
- painel administrativo e estatísticas;
- backup, importação, exportação e atualização;
- consolidação do produto para uso diário.

## Integração atual

O portal mantém separadas as bases já desenvolvidas:

- `web/app.py`: ATAS-JMCM homologado, sem alterações;
- `portal/app.py`: Licita Suite-JM.adm;
- Central de Processos: acompanhamento operacional;
- Gerar atas: integração com o motor 4.0 LTS Build v2.2;
- FOCO DOCS: classificação, checklist, relatório e ZIP organizado.

O fluxo atual do FOCO DOCS já executa processamento de um clique sobre o ZIP.
OCR completo, integrações públicas, banco persistente, PWA offline e motor de
regras avançado permanecem como próximas camadas, pois exigem infraestrutura
específica e validação própria.

## Portal de Compras Públicas

O fluxo operacional informado utiliza:

- número do pregão;
- órgão comprador `ICISMEP`;
- busca pública em `processos?processo=...&orgao=ICISMEP`.

O FOCO DOCS gera essa busca diretamente. A transferência automática sem
download depende da API oficial oferecida pelo Portal para parceiros e
compradores. A interface deixa o conector preparado e aponta para a solicitação
oficial de integração; não utiliza endpoints privados nem contorna autenticação.
