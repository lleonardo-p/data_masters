# Fluxo Batch de Dengue

Este documento descreve o fluxo Batch implementado para processar os arquivos
públicos de notificações de dengue de 2024, 2025 e do período parcial de 2026.
O objetivo é demonstrar engenharia de dados de ponta a ponta: recebimento,
processamento distribuído, qualidade, modelagem, catálogo, reconciliação e
consumo analítico.

## Diagrama do processo Batch

> **Evidência a adicionar:** diagrama completo do fluxo, da entrega do arquivo
> até as views no Athena.

<!--
![Arquitetura completa do fluxo Batch](../../architecture/c4/batch/batch-end-to-end.png)
-->

```text
Arquivo oficial -> S3 Staging -> Step Functions
                -> Glue Bronze -> Glue Silver + Quarentena
                -> Glue Gold -> Reconciliação -> Glue Crawler
                -> Glue Data Catalog -> Athena -> Views analíticas
```

## Visão geral

| Etapa | Responsabilidade | Resultado |
|---|---|---|
| Staging | Receber o arquivo oficial sem transformação | CSV anual identificado pelo ano de referência |
| Bronze | Preservar o conteúdo da fonte e acrescentar linhagem técnica | Parquet/Snappy particionado |
| Silver | Tipar, normalizar, enriquecer, deduplicar e aplicar qualidade | Casos válidos ou com alerta |
| Quarentena | Isolar registros que violam regras bloqueantes | Registros rejeitados com códigos de erro e rastreabilidade |
| Gold | Organizar os casos para análise | Uma fato e cinco dimensões |
| Catálogo e Athena | Descobrir o schema e expor interfaces SQL | Tabelas e views analíticas |
| Reconciliação | Comprovar que o lote fechou entre as camadas | Manifesto JSON e falha bloqueante em divergências |

## 1. Fonte e entrada na Staging

Os arquivos foram obtidos nos canais oficiais do Ministério da Saúde:

- [Transferência de Arquivos do DATASUS](https://datasus.saude.gov.br/transferencia-de-arquivos/);
- [Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/).

No MVP, o upload é manual e representa um cenário real de *file intake*: um
órgão público, cliente ou parceiro entrega extratos periódicos, e um operador
autorizado os posiciona na zona de recebimento da plataforma.

```text
staging/opendatasus/dengue/reference_year=2024/DENGBR24.csv
staging/opendatasus/dengue/reference_year=2025/DENGBR25.csv
staging/opendatasus/dengue/reference_year=2026/DENGBR26.csv
```

### Por que o fluxo não usa a API

A API avaliada não apresentou paginação determinística para a extração
histórica: chamadas equivalentes podiam devolver conjuntos diferentes e não
havia uma combinação confiável de ordenação, `offset` e identificador estável
para implementar checkpoint, retomada e prova de completude. Usá-la poderia
produzir lacunas ou duplicidades difíceis de detectar.

Os arquivos anuais oficiais foram escolhidos por oferecerem uma unidade de
entrega reproduzível e adequada a backfill. A automação da obtenção dos arquivos
é uma evolução possível, mas não deve substituir confiabilidade por uma
integração aparentemente automática e não determinística.

> A Staging é uma zona de entrada. O arquivo não é corrigido nela, o que mantém
> separadas a responsabilidade do produtor e as transformações da plataforma.

## 2. Orquestração e identidade do lote

A state machine `baip-dev-dengue-batch-pipeline` executa, de forma síncrona:

1. Bronze;
2. Silver e quarentena;
3. Gold;
4. reconciliação;
5. crawler da Gold.

O nome da execução da Step Functions é propagado como `batch_id` para todos os
jobs. Esse identificador permite correlacionar registros, logs e o manifesto de
reconciliação sem depender apenas do horário da carga.

A execução é **sob demanda**; não existe agendamento recorrente implementado.
CloudWatch registra falhas da orquestração e alarmes publicam eventos em um
tópico SNS para execuções com estado `FAILED`, `TIMED_OUT` ou `ABORTED`.

## 3. Bronze — preservação e padronização técnica

O job `bronze_ingestion.py` lê recursivamente os CSVs da Staging e aplica um
contrato estrutural explícito com as 121 colunas dos arquivos `DENGBR`.

Decisões implementadas:

- leitura em `FAILFAST`, para não ignorar silenciosamente uma quebra de schema;
- manutenção dos campos de origem como `string`, adiando a interpretação
  semântica para a Silver;
- normalização técnica dos nomes das colunas;
- inclusão de `_batch_id`, arquivo de origem, sistema, formato, ambiente e
  instante de carga;
- derivação do ano de referência a partir do caminho do arquivo;
- conversão para Parquet com compressão Snappy;
- métricas de volume, data de notificação inválida, ano desconhecido e agravo
  desconhecido nos logs do job.

A saída é particionada por:

```text
disease/reference_year/notification_year/notification_month
```

O Parquet reduz leitura e armazenamento nas etapas seguintes. O particionamento
mensal atende às consultas históricas por período sem criar a quantidade de
metadados e pequenos arquivos que uma partição diária produziria neste volume.
A Bronze não descarta registros por regra de negócio: ela preserva a evidência
recebida e sustenta auditoria e reprocessamento.

## 4. Silver — contrato analítico e qualidade

O job `silver_dengue_cases.py` transforma a representação técnica da Bronze em
um contrato de casos de dengue utilizável pela Gold.

As principais tratativas são:

- padronização de `""`, `nan`, `null` e `none` como nulo;
- conversão controlada de datas, inteiros, códigos e booleanos;
- decodificação de classificação, critério de confirmação, evolução,
  hospitalização, sexo, gestação, raça, escolaridade e autoctonia;
- interpretação da idade codificada e criação de faixas etárias;
- derivação de indicadores como caso confirmado, descartado, grave,
  hospitalizado e óbito;
- enriquecimento dos municípios de residência, notificação e infecção com nome,
  UF e região da referência do IBGE;
- criação de um hash SHA-256 das 121 colunas de negócio e de um `record_id`
  determinístico;
- detecção de duplicatas exatas, necessária porque a fonte não fornece um
  identificador estável do registro.

Somente as colunas necessárias ao produto analítico seguem para a Silver. As
demais continuam preservadas na Bronze e podem entrar em uma futura versão do
contrato sem alterar a evidência original.

### Erros, alertas e quarentena

As regras possuem duas severidades:

| Severidade | Exemplos | Tratamento |
|---|---|---|
| Erro bloqueante | data inválida ou futura, município de residência ausente/não encontrado, identidade do lote ausente ou divergente, cronologia impossível, duplicata exata | Registro enviado à quarentena |
| Alerta | classificação ausente/não mapeada, hospitalização ignorada, município de notificação/infecção não encontrado, ano de referência diferente do ano de notificação | Registro permanece na Silver com status `warning` |

A quarentena evita dois extremos: contaminar a camada analítica ou interromper
todo o lote por erros pontuais. O registro rejeitado conserva os dados tratados,
o `batch_id`, o arquivo de origem, todos os códigos de erro, o erro principal e
o instante da rejeição. Assim, é possível investigar a causa, corrigir a regra
ou a referência e reprocessar o lote.

```text
silver/opendatasus/dengue/cases/
quarantine/opendatasus/dengue/silver_cases/
```

A Silver é particionada por doença, ano de referência, ano e mês de
notificação. A quarentena é particionada por erro principal, ano de referência
e período da rejeição.

### Evidência — quarentena no S3

> **Evidência a adicionar:** captura do prefixo da quarentena no S3, mostrando
> as partições por `primary_error_code` e um exemplo de registro rastreável.

<!--
![Registros da Silver enviados à quarentena](assets/s3-silver-quarantine.png)
-->

## 5. Gold — modelo dimensional

O job `gold_dengue_star_schema.py` aceita registros Silver com status `valid` ou
`warning`. Registros em quarentena não entram no modelo dimensional.

### Tabela fato

`fact_dengue_cases` possui o grão explícito de **uma linha por `record_id`
único da Silver**. O job falha se encontrar duplicidade nesse grão.

A fato mantém:

- `case_id`, `record_hash`, `source_batch_id` e metadados de linhagem;
- chaves para doença, datas, localidades, perfil demográfico e perfil clínico;
- semana epidemiológica da notificação e do início dos sintomas;
- medidas binárias e aditivas: notificações, confirmados, descartados, sinais de
  alarme, graves, em investigação, hospitalizados, óbitos, autóctones e casos
  com alerta de qualidade;
- status e códigos de alerta de qualidade;
- partições por ano e mês da notificação.

Medidas `0/1` permitem agregações por qualquer combinação das dimensões sem
reimplementar as regras de classificação em cada consulta.

### Dimensões

| Dimensão | Chave | Conteúdo e função |
|---|---|---|
| `dim_date` | `date_key` | Calendário compartilhado pelos papéis de notificação, sintomas, investigação, digitação, internação, encerramento e óbito |
| `dim_location` | `location_key` | Município SINAN/IBGE, UF e região; reutilizada para residência, notificação e infecção |
| `dim_disease` | `disease_key` | Código e nome do agravo |
| `dim_demographic` | `demographic_key` | Idade, faixa etária, sexo, gestação, raça e escolaridade |
| `dim_clinical` | `clinical_key` | Classificação, critério, evolução, hospitalização, autoctonia e sorotipo |

As chaves de doença, perfil demográfico e perfil clínico são determinísticas,
geradas com `xxhash64` sobre seus atributos de negócio. Datas usam `yyyyMMdd` e
localidades usam o código IBGE. Cada dimensão possui a chave `-1` para membro
desconhecido, preservando integridade referencial quando um atributo opcional
não está disponível.

> Os hashes usados como identidade e chave técnica atendem deduplicação e
> estabilidade do modelo; eles não devem ser interpretados como anonimização ou
> mecanismo criptográfico de proteção de PII.

## 6. Reconciliação, catálogo e consumo no Athena

Antes de publicar o catálogo, o job de reconciliação verifica:

- `Bronze = Silver + quarentena` para o lote atual;
- `Gold = Silver`;
- consistência do `batch_id` entre as camadas;
- unicidade do grão da fato e das chaves das dimensões;
- ausência de chaves estrangeiras órfãs;
- medidas da fato limitadas a `0` ou `1`;
- fechamento dos status `valid` e `warning` da Silver.

Qualquer divergência faz o job falhar. O resultado também é gravado como JSON
em `pipeline-runs/dengue-batch/reconciliation/batch_id=<batch_id>/`, formando
uma evidência auditável da execução.

Depois da reconciliação, o crawler atualiza o database `baip_dev_gold` no Glue
Data Catalog. Ele registra seis tabelas com prefixo `dengue_`: uma fato e cinco
dimensões. O Athena consulta esses metadados diretamente sobre o S3.

As views versionadas no repositório expõem:

- casos enriquecidos;
- indicadores mensais por município;
- indicadores mensais por UF;
- indicadores por faixa etária;
- indicadores por classificação;
- dataset agregado para consumo analítico.

As views separam a interface de consumo do layout físico das tabelas e evitam
que cada analista replique joins e regras de agregação.

### Evidência — Athena

> **Evidência a adicionar:** captura da execução dos testes de aceitação e de uma
> consulta sobre as views, com tabelas, filtros e resultado visíveis.

<!--
![Validação e consumo do batch no Athena](assets/athena-batch-evidence.png)
-->

## Resultado de referência

Uma execução completa já produziu o seguinte fechamento:

| Camada/estado | Registros |
|---|---:|
| Bronze | 8.617.612 |
| Silver | 8.553.989 |
| Silver `valid` | 5.652.824 |
| Silver `warning` | 2.901.165 |
| Quarentena | 63.623 |
| Gold — fato | 8.553.989 |

Nessa execução, não foram encontrados casos duplicados na fato, medidas fora de
`0/1`, chaves de dimensão duplicadas ou chaves estrangeiras órfãs. Os cinco
testes de aceitação SQL do Athena também foram aprovados.

## Controles de engenharia demonstrados

- **Reprodutibilidade:** infraestrutura, jobs, consultas e views versionados;
- **Rastreabilidade:** `batch_id`, arquivo de origem, hashes e timestamps entre
  as camadas;
- **Idempotência do snapshot:** escrita em `overwrite` evita acumular cópias ao
  reexecutar a mesma entrada;
- **Qualidade:** contrato estrutural, erros bloqueantes, alertas e quarentena;
- **Auditabilidade:** reconciliação materializada em JSON e logs correlacionados;
- **Segurança:** buckets sem acesso público, versionamento, criptografia SSE-S3,
  ownership pelo proprietário do bucket e roles IAM específicas dos serviços;
- **Observabilidade:** métricas dos jobs, logs da Step Functions, alarmes
  CloudWatch e SNS para falhas terminais;
- **Custo e desempenho:** Parquet/Snappy, partições mensais e limite de bytes por
  consulta no workgroup do Athena.

Os arquivos públicos de saúde continuam sujeitos a governança. Origem pública
não significa acesso irrestrito aos buckets nem dispensa controles de auditoria.

## Limites atuais e evolução

O pipeline representa um snapshot completo e deve ser executado de forma
serial: duas execuções concorrentes escreveriam nos mesmos paths com
`overwrite`. Para cargas frequentes ou múltiplos produtores, a evolução deve
incluir bloqueio de concorrência, manifestos de entrega, checksum e
processamento apenas das partições recebidas.

Com aumento de volume, os primeiros passos são medir shuffle, spill, duração,
tamanho dos arquivos e bytes escaneados; ajustar partições e Glue Auto Scaling;
e adicionar compactação. EMR passa a ser alternativa quando houver necessidade
comprovada de controle de cluster, bibliotecas/runtime específicos ou workloads
longos. Apache Iceberg pode ser considerado para `upsert`, evolução de schema,
dados atrasados e snapshots transacionais.

## Implementação relacionada

- [Job Bronze](../../src/glue/jobs/bronze_ingestion/bronze_ingestion.py)
- [Job Silver](../../src/glue/jobs/silver_dengue_cases/silver_dengue_cases.py)
- [Job Gold](../../src/glue/jobs/gold_dengue_star_schema/gold_dengue_star_schema.py)
- [Reconciliação do lote](../../src/glue/jobs/reconcile_dengue_batch/reconcile_dengue_batch.py)
- [Orquestração Step Functions](../../infra/terraform/environments/dev/dengue_batch_orchestration.tf)
- [Infraestrutura principal](../../infra/terraform/environments/dev/main.tf)
- [Views e validações Athena](../../src/athena/dengue/)
- [ADRs](../../architecture/ADR/)