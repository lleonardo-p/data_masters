# ADR-013: Orquestração com AWS Step Functions e EventBridge

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui pipelines batch diários, cargas históricas, validações, transformações, publicação de dados analíticos e possíveis execuções parametrizadas de backfill.

A arquitetura precisa coordenar etapas, controlar dependências, tratar falhas e permitir agendamento sem administrar infraestrutura de orquestração.

## Decisão

A orquestração do MVP será feita com **AWS Step Functions** e **Amazon EventBridge Scheduler**.

O EventBridge Scheduler será utilizado para disparar execuções agendadas.

O Step Functions será utilizado para coordenar etapas do pipeline, incluindo:

- extração;
- validação;
- processamento Glue;
- atualização de catálogo;
- publicação de camadas Silver/Gold/DW;
- notificações e tratamento de falhas.

Backfills deverão ser modelados como execuções parametrizadas, evitando alterar o fluxo diário padrão.

A arquitetura deve evitar uma DAG única e excessivamente acoplada. Os fluxos deverão ser separados por domínio, fonte ou responsabilidade quando fizer sentido.

## Justificativa

Step Functions permite orquestrar fluxos serverless com controle de estados, retries, tratamento de erro e rastreabilidade visual.

EventBridge Scheduler atende ao agendamento de execuções recorrentes sem necessidade de manter um scheduler próprio.

A combinação é adequada ao MVP por ser gerenciada, integrada à AWS e suficiente para coordenar pipelines batch sem introduzir Airflow ou outra plataforma de orquestração mais pesada.

## Alternativas consideradas

- **Apache Airflow/MWAA:** forte para DAGs complexas, mas adiciona custo e complexidade operacional para o MVP.
- **Control-M:** adequado em ambientes corporativos, mas fora do escopo de uma arquitetura AWS serverless para portfólio.
- **Cron em EC2:** simples, mas pouco resiliente e com maior responsabilidade operacional.
- **EventBridge sem Step Functions:** atende agendamento, mas não oferece orquestração visual, controle de estados e tratamento estruturado de falhas.

## Consequências

### Positivas

- Orquestração gerenciada.
- Boa integração com Glue, Lambda, SNS e CloudWatch.
- Suporte a retries e tratamento de erro.
- Execuções rastreáveis e parametrizadas.
- Simplicidade para agendamento de pipelines batch.
- Possibilidade de separar fluxo diário e backfill.

### Negativas / Trade-offs

- Pode ficar limitado para DAGs muito complexas.
- Fluxos grandes podem se tornar difíceis de manter.
- Exige modelagem adequada de estados e exceções.
- Pode gerar custo por transição de estado em cenários de alta frequência.

## Escalabilidade e alternativas

Pipelines serão separados por produto e usarão parâmetros como `run_date`,
`batch_id` e `is_backfill`. Concorrência de backfill deve ser limitada para não
esgotar quotas do Glue ou pressionar S3 e APIs. Distributed Map é alternativa
para fan-out controlado, com checkpoint e idempotência.

MWAA/Airflow passa a ser avaliado quando dependências entre muitos domínios,
calendários, sensores, SLA e operação por múltiplas equipes superarem state
machines independentes. Transições de estado e histórico também possuem custo e
quotas que devem ser monitorados.

## Critérios de evolução

Esta decisão deve ser revisada se:

- a quantidade de pipelines crescer significativamente;
- houver muitas dependências entre domínios;
- for necessário recurso avançado de scheduler, calendário ou SLA;
- múltiplos times precisarem operar DAGs independentes;
- houver necessidade de ambiente de orquestração mais completo, como Airflow/MWAA.

## Referências

- AWS Step Functions
- Amazon EventBridge Scheduler
- AWS Glue Jobs
- AWS Lambda
- Amazon CloudWatch
