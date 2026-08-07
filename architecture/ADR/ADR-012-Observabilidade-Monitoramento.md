# ADR-012: Observabilidade e Monitoramento

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

Os fluxos Batch e NRT precisam registrar execuções, falhas, duração, volume processado e mensagens rejeitadas. A observabilidade deve permitir localizar problemas sem expor dados pessoais nos logs.

## Decisão

Centralizar logs, métricas e alarmes no Amazon CloudWatch.

A observabilidade contempla:

* logs das funções AWS Lambda;
* logs e métricas dos jobs AWS Glue;
* histórico e falhas da Step Functions;
* métricas do Amazon SQS e da DLQ;
* logs de acesso e erros da API NRT;
* métricas de consultas do Athena;
* alarmes para falhas, timeouts, filas acumuladas, mensagens na DLQ e erros da API;
* notificações de alarmes por Amazon SNS.

Os logs utilizam identificadores técnicos, como `batch_id`, `event_id` e `message_id`, sem registrar CPF, nome, telefone ou e-mail.

## Justificativa

O CloudWatch possui integração nativa com os serviços utilizados e permite centralizar o monitoramento sem provisionar outra infraestrutura.

Os identificadores técnicos relacionam os eventos da mesma execução e facilitam a investigação de falhas. O relatório de reconciliação complementa o monitoramento técnico com verificações de qualidade dos dados.

## Limitação atual

Os logs permanecem no Amazon CloudWatch e não são encaminhados para uma plataforma externa ou central corporativa de observabilidade.

Não foram implementadas integrações com Grafana, Prometheus, OpenSearch, Splunk ou Datadog. Essa limitação é aceitável para o MVP, mas reduz a capacidade de criar painéis unificados, correlacionar eventos e manter análises históricas de longo prazo.

## Melhorias futuras

Uma evolução produtiva poderá incluir:

* centralização dos logs de diferentes ambientes e contas;
* dashboards operacionais no Amazon Managed Grafana;
* métricas customizadas e indicadores de nível de serviço;
* rastreamento distribuído com AWS X-Ray;
* arquivamento de logs no Amazon S3;
* correlação automática entre `batch_id`, `event_id` e alarmes;
* integração com uma plataforma corporativa de observabilidade.

## Alternativas

* **Prometheus e Grafana:** não adotados porque exigiriam configuração, integração e manutenção adicionais.
* **Amazon OpenSearch Service:** não adotado devido ao custo e à complexidade para o volume atual de logs.
* **Plataforma externa de observabilidade:** não adotada por não fazer parte do escopo e adicionar custos de licenciamento ou ingestão.
* **Logs armazenados somente no Amazon S3:** não adotados porque dificultariam consultas e alarmes operacionais imediatos.
