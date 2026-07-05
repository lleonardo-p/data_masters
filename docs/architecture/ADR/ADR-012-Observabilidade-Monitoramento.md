# ADR-012: Observabilidade e Monitoramento

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui pipelines batch, fluxo near real-time, armazenamento em Data Lake, APIs, dashboards e componentes serverless.

A operação precisa detectar falhas, atrasos, aumento de custo, erro de dados, mensagens presas em fila e problemas de performance.

## Decisão

A observabilidade será baseada em **Amazon CloudWatch**, complementada por serviços de auditoria e custo.

Devem ser monitorados:

- execução de Glue Jobs;
- falhas em Lambda;
- mensagens na SQS e DLQ;
- latência e erros no fluxo near real-time;
- custos e anomalias de consumo;
- freshness dos datasets;
- volume de registros por fonte;
- logs sem PII.

Para produção, a arquitetura deve incluir CloudTrail, AWS Config, Budgets/Cost Anomaly Detection e alarmes via SNS ou integração equivalente.

## Justificativa

CloudWatch integra nativamente com os serviços AWS usados e reduz complexidade operacional no MVP.

A observabilidade precisa cobrir operação técnica, qualidade dos dados e custo.

## Alternativas consideradas

- **Datadog/New Relic:** ferramentas robustas, mas adicionam custo para o MVP.
- **Logs locais:** insuficientes para operação cloud.
- **Monitoramento apenas manual:** não atende boas práticas operacionais.

## Consequências

### Positivas

- Maior visibilidade operacional.
- Detecção rápida de falhas.
- Melhor controle de custo.
- Base para melhoria contínua.

### Negativas

- Exige configuração de métricas e alarmes.
- Logs podem gerar custo se a retenção não for controlada.
- Métricas mal definidas podem gerar ruído operacional.

## Critérios de evolução

Revisar esta decisão se:

- houver múltiplos times operando a plataforma;
- SLAs formais forem definidos;
- logs e métricas crescerem muito em custo;
- rastreabilidade distribuída se tornar requisito.

## Referências

- Amazon CloudWatch
- AWS CloudTrail
- AWS Budgets
- AWS Well-Architected Operational Excellence
