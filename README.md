# BAIP — Plataforma de Engenharia de Dados para Dengue

## Apresentação

O BAIP é uma plataforma de engenharia de dados criada para demonstrar, de forma prática, decisões arquiteturais e técnicas aplicadas a pipelines de dados em nuvem.

O projeto explora dois modelos de processamento:

- **Batch:** processamento de arquivos históricos de casos de dengue;
- **NRT — Near Real Time:** processamento orientado a eventos de triagens hospitalares simuladas.

O domínio de dengue foi escolhido para manter os dois fluxos dentro de um mesmo contexto de negócio.

A proposta não é produzir um sistema epidemiológico oficial, mas demonstrar a construção de produtos de dados desde a ingestão até a disponibilização das informações para consumo.

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
- consultas SQL;
- disponibilização de indicadores.

## Escopo

A plataforma possui dois fluxos de processamento:

| Fluxo | Entrada | Processamento | Consumo | Estado |
|---|---|---|---|---|
| Batch | Arquivos governamentais de dengue | Staging, Bronze, Silver e Gold | Views no Athena | Implementado |
| NRT | Eventos sintéticos de triagem hospitalar | Mensageria e processamento orientado a eventos | Indicadores disponibilizados por API | Planejado |

Não fazem parte do escopo atual:

- ingestão diária por APIs externas;
- processamento de dados de Zika ou Chikungunya;
- publicação de dashboards;
- utilização de dados reais de pacientes no fluxo NRT.

## Fonte dos dados

O fluxo Batch utiliza arquivos públicos de notificações de dengue referentes aos seguintes períodos:

- 2024;
- 2025;
- janeiro a julho de 2026.

Os arquivos foram obtidos nos canais oficiais do Ministério da Saúde:

- [Transferência de Arquivos do DATASUS](https://datasus.saude.gov.br/transferencia-de-arquivos/);
- [Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/).

O arquivo de 2026 representa um período parcial e pode sofrer alterações em novas publicações da fonte.

A entrada manual dos arquivos na Staging representa um processo controlado de recebimento de dados de um órgão público, parceiro ou cliente.

Esse modelo é aplicável quando a fonte disponibiliza arquivos periódicos ou quando não existe uma API estável para integração automatizada.

## Decisões arquiteturais

As principais decisões do projeto estão registradas como *Architecture Decision Records*.

Cada ADR documenta:

- o contexto da decisão;
- as alternativas consideradas;
- a solução escolhida;
- as consequências da escolha;
- as possibilidades de evolução.

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
- escalabilidade;
- recuperação de desastre.

## Fluxos da plataforma

A documentação detalhada de cada fluxo é mantida separadamente.

### Fluxo Batch

Processamento dos arquivos governamentais de dengue desde a entrada manual na Staging até a disponibilização de views analíticas no Athena.

- [Documentação do fluxo Batch](docs/batch/README.md)

### Fluxo NRT

Processamento de eventos sintéticos de triagem hospitalar, incluindo mensageria, proteção de dados PII, geração de indicadores e disponibilização por API.

- [Documentação do fluxo NRT](docs/nrt/README.md)

## Diagramas de arquitetura

Os diagramas da plataforma são organizados utilizando o modelo C4:

```text
architecture/c4/
```

Cada fluxo terá seus próprios diagramas de contexto, containers e componentes:

```text
architecture/c4/
├── batch/
└── nrt/
```

- `architecture/c4/batch/` — diagramas do fluxo Batch;
- `architecture/c4/nrt/` — diagramas do fluxo NRT.

> Os diagramas serão adicionados durante a documentação detalhada de cada fluxo.

## Instalação da plataforma

O provisionamento da infraestrutura utiliza Terraform. As operações e validações complementares são executadas por scripts Bash e AWS CLI.

O guia de instalação apresenta:

- os pré-requisitos locais;
- a configuração do profile AWS;
- a criação do backend Terraform;
- o provisionamento da infraestrutura;
- a preparação dos arquivos de referência;
- a carga manual dos arquivos na Staging;
- a execução do pipeline;
- a validação dos resultados;
- a remoção dos recursos provisionados.

- [Guia de instalação da plataforma](docs/usage/installation.md)

## Tecnologias

### Batch

- Amazon S3;
- AWS Glue;
- Apache Spark e PySpark;
- AWS Step Functions;
- AWS Glue Data Catalog;
- AWS Glue Crawler;
- Amazon Athena;
- Amazon CloudWatch;
- Amazon SNS;
- Terraform.

### NRT — planejado

- Amazon SQS;
- AWS Lambda;
- Amazon DynamoDB;
- Amazon API Gateway;
- AWS KMS;
- Amazon CloudWatch;
- Terraform.

## Observação sobre os dados

Os arquivos governamentais utilizados no fluxo Batch são públicos, mas podem conter limitações de qualidade, atualização e interpretação definidas pela fonte.

Os eventos utilizados no fluxo NRT serão exclusivamente sintéticos. Nenhuma informação real de paciente será utilizada.

O tratamento de PII no fluxo NRT tem finalidade demonstrativa e será aplicado para explorar conceitos de segurança, privacidade, pseudonimização e proteção de dados relacionados à LGPD.