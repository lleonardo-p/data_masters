# BAIP — Plataforma de Engenharia de Dados para Dengue

## Apresentação

O BAIP é um projeto de plataforma de engenharia de dados criado para demonstrar, de forma prática, decisões arquiteturais e técnicas aplicadas a pipelines de dados em nuvem.

O projeto explora dois modelos de processamento:

- **Batch:** processamento de arquivos históricos de casos de dengue;
- **NRT — Near Real Time:** processamento orientado a eventos de triagens hospitalares simuladas.

O domínio de dengue foi escolhido para manter os dois fluxos dentro de um mesmo contexto de negócio. A proposta principal não é produzir um sistema epidemiológico oficial, mas demonstrar a construção de produtos de dados desde a entrada da informação até sua disponibilização para consumo.

## Objetivo

O objetivo do projeto é apresentar conceitos de engenharia de dados aplicados de ponta a ponta, incluindo:

- ingestão de arquivos e eventos;
- arquitetura Medallion;
- processamento distribuído;
- qualidade e quarentena de dados;
- padronização e enriquecimento;
- idempotência e rastreabilidade;
- orquestração de pipelines;
- modelagem dimensional;
- catálogo de dados;
- reconciliação entre camadas;
- segurança e tratamento de dados pessoais;
- infraestrutura como código;
- observabilidade;
- consultas SQL e disponibilização de indicadores.

## Escopo

A plataforma possui somente dois casos:

| Fluxo | Entrada | Processamento | Consumo | Estado |
|---|---|---|---|---|
| Batch | Arquivos governamentais de dengue | Staging, Bronze, Silver e Gold | Views no Athena | Implementado |
| NRT | Eventos sintéticos de triagem hospitalar | Mensageria e processamento orientado a eventos | Indicadores disponibilizados por API | Planejado |

Não fazem parte do escopo atual:

- ingestão diária de APIs externas;
- dados de Zika ou Chikungunya;
- publicação de dashboard;
- utilização de dados reais de pacientes no fluxo NRT.

## Fonte dos dados

O fluxo Batch utiliza arquivos públicos de notificações de dengue referentes aos anos de:

- 2024;
- 2025;
- janeiro a julho de 2026.

Os arquivos foram obtidos nos canais oficiais do Ministério da Saúde:

- [Transferência de Arquivos do DATASUS](https://datasus.saude.gov.br/transferencia-de-arquivos/);
- [Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/).

O arquivo de 2026 representa um período parcial e pode sofrer alterações em novas publicações da fonte.

## Decisões arquiteturais

As principais decisões do projeto estão registradas como *Architecture Decision Records*.

Cada ADR documenta o contexto, as alternativas consideradas, a decisão adotada, suas consequências e possibilidades de evolução.

- [Architecture Decision Records](architecture/ADR/)

Os ADRs cobrem temas como:

- escolha da AWS;
- Data Lake no Amazon S3;
- processamento Batch com AWS Glue;
- mensageria e processamento NRT;
- segurança e governança;
- tratamento de dados PII;
- qualidade e observabilidade;
- modelagem dimensional;
- catálogo de dados;
- orquestração;
- particionamento;
- escalabilidade e recuperação de desastre.

## Diagramas de arquitetura

Os diagramas serão organizados utilizando o modelo C4:

```text
architecture/c4/