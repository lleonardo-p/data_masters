# ADR-013: Orquestração com Step Functions e EventBridge

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

Os pipelines do BAIP precisam executar etapas dependentes, como ingestão, validação, transformação, geração de Gold, atualização de catálogo e publicação de indicadores.

A solução precisa ser rastreável, gerenciada e simples para o MVP.

## Decisão

A orquestração será feita com **AWS Step Functions**, com agendamentos via **Amazon EventBridge Scheduler**.

As state machines devem ser separadas por domínio ou fluxo principal, evitando uma DAG única e excessivamente acoplada.

Step Functions deve coordenar jobs Glue, Lambdas e etapas de validação, mantendo controle de retries, falhas e status da execução.

## Justificativa

Step Functions oferece orquestração gerenciada, visualização de estado, controle de erro e integração com serviços AWS.

EventBridge Scheduler permite execuções programadas sem necessidade de manter um orquestrador próprio.

## Alternativas consideradas

- **Apache Airflow/MWAA:** excelente para orquestração de dados, mas mais complexo e caro para o MVP.
- **Cron em servidor:** simples, mas frágil e pouco observável.
- **Glue Workflows:** integrado ao Glue, mas menos flexível para orquestrar múltiplos serviços.

## Consequências

### Positivas

- Orquestração gerenciada.
- Melhor rastreabilidade de execução.
- Controle de retries e falhas.
- Baixo esforço operacional.

### Negativas

- Pode ficar caro ou complexo com workflows muito grandes.
- Requer disciplina na decomposição das state machines.
- Menor flexibilidade que Airflow para dependências muito complexas.

## Critérios de evolução

Revisar esta decisão se:

- os pipelines virarem muitas DAGs interdependentes;
- houver necessidade de backfill complexo;
- múltiplos times precisarem gerenciar workflows;
- dependências entre fontes ficarem difíceis de modelar em Step Functions.

## Referências

- AWS Step Functions
- Amazon EventBridge Scheduler
- AWS Glue Jobs
