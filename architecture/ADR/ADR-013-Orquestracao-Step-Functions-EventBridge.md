# ADR-013: Orquestração com AWS Step Functions e EventBridge

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui cargas por arquivos, planeja ingestões diárias, executa validações,
transformações, publicação de dados analíticos e possíveis backfills
parametrizados.

A arquitetura precisa coordenar etapas, controlar dependências, tratar falhas e permitir agendamento sem administrar infraestrutura de orquestração.

## Decisão

A orquestração será feita com **AWS Step Functions**. O **Amazon EventBridge
Scheduler** será utilizado apenas nos fluxos que possuírem recorrência definida.

O batch de dengue atual começa após a entrega manual governada do arquivo e,
portanto, é iniciado sob demanda. Não existe recorrência automática nesse fluxo.
O caso de API externa diária poderá usar EventBridge Scheduler quando for
implementado.

O Step Functions será utilizado para coordenar etapas do pipeline, incluindo:

- extração, quando fizer parte do fluxo;
- validação;
- processamento Glue;
- atualização de catálogo;
- publicação de camadas Silver/Gold/DW;
- notificações e tratamento de falhas.

Backfills deverão ser modelados como execuções parametrizadas, evitando alterar
o fluxo operacional padrão.

A arquitetura deve evitar uma DAG única e excessivamente acoplada. Os fluxos deverão ser separados por domínio, fonte ou responsabilidade quando fizer sentido.

## Justificativa

Step Functions permite orquestrar fluxos serverless com controle de estados,
tratamento de erro e rastreabilidade visual. Retry automático deve ser aplicado
somente quando a etapa for idempotente e o erro for transitório.

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
- Suporte a tratamento de erro e retries explicitamente configurados.
- Execuções rastreáveis e parametrizadas.
- Simplicidade para agendamento de pipelines batch.
- Possibilidade de separar fluxo diário e backfill.

### Negativas / Trade-offs

- Pode ficar limitado para DAGs muito complexas.
- Fluxos grandes podem se tornar difíceis de manter.
- Exige modelagem adequada de estados e exceções.
- Pode gerar custo por transição de estado em cenários de alta frequência.

## Estado implementado no batch de dengue

A state machine executa Bronze, Silver, Gold, reconciliação e crawler. Ela usa
o nome da execução como `batch_id`, possui timeout global e falha quando uma
etapa falha. O retry atual é uma nova execução completa com nome único; não há
retry automático de jobs de dados para evitar reprocessamento implícito.

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
