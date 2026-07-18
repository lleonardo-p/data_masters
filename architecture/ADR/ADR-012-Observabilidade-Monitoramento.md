# ADR-012: Observabilidade e Monitoramento

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui pipelines batch, fluxo near real-time, filas, funções Lambda, jobs Glue, tabelas no S3, indicadores no DynamoDB e consultas analíticas no Athena.

A arquitetura precisa permitir acompanhamento de falhas, latência, custo, freshness, volumetria, qualidade e saúde operacional dos componentes.

## Decisão

A observabilidade será estruturada em três dimensões:

- **Operacional:** falhas, duração de jobs, retries, DLQ, erros de Lambda, execuções Step Functions e status de pipelines.
- **Dados:** freshness, volumetria, quantidade de registros, qualidade, duplicidade, registros em quarentena e variações inesperadas.
- **Custo:** consumo de Glue DPU, dados escaneados no Athena, invocações Lambda, capacidade/uso do DynamoDB e armazenamento S3.

A arquitetura utilizará principalmente:

- Amazon CloudWatch para logs, métricas e alarmes;
- CloudWatch Alarms para falhas críticas e DLQ;
- AWS CloudTrail para auditoria de ações na conta quando aplicável;
- AWS Budgets e Cost Anomaly Detection para controle de custo;
- notificações via SNS ou mecanismo equivalente em cenários produtivos.

Logs não devem conter CPF, PII ou payloads sensíveis.

## Justificativa

Observabilidade é necessária para operar pipelines de dados com confiabilidade, identificar falhas rapidamente e evitar que problemas de qualidade ou custo passem despercebidos.

Separar observabilidade operacional, de dados e de custo facilita a priorização dos alertas e evita tratar todos os sinais como falhas técnicas.

CloudWatch é a escolha natural para o MVP por ser integrado aos serviços AWS utilizados na arquitetura.

## Alternativas consideradas

- **Monitoramento manual:** simples no início, mas não escala e aumenta risco de falhas não percebidas.
- **Ferramentas externas como Datadog ou New Relic:** oferecem recursos avançados, mas adicionam custo e complexidade ao MVP.
- **Apenas logs sem métricas:** dificulta análise histórica, alertas e acompanhamento de tendências.
- **Observabilidade apenas técnica:** ignora problemas de dados, como freshness, volumetria e qualidade.

## Consequências

### Positivas

- Melhor visibilidade operacional dos pipelines.
- Detecção mais rápida de falhas.
- Controle de DLQ e retries.
- Acompanhamento de freshness e volumetria.
- Redução de risco de aumento inesperado de custo.
- Base para operação mais profissional em produção.

### Negativas / Trade-offs

- Exige configuração de métricas, alarmes e retenção de logs.
- Pode gerar ruído se alertas não forem bem calibrados.
- Logs e métricas também geram custo.
- Necessita manutenção conforme novos pipelines forem adicionados.

## Escalabilidade e alternativas

Métricas devem ter dimensões controladas; usar `event_id` como dimensão gera
alta cardinalidade e custo. Logs estruturados precisam de retenção por ambiente
e sampling quando volume crescer, sem perder erros e auditoria.

Com mais domínios, SLOs, painéis e alarmes devem ser definidos por produto de
dados. OpenTelemetry e plataformas externas serão avaliados quando correlação
entre contas/regiões e volume operacional superarem o CloudWatch do MVP.

## Critérios de evolução

Esta decisão deve ser revisada se:

- o número de pipelines crescer significativamente;
- houver necessidade de SLO/SLA formal;
- múltiplos times precisarem operar a plataforma;
- o volume de alertas se tornar alto;
- houver necessidade de dashboards operacionais dedicados;
- a arquitetura evoluir para produção crítica.

## Referências

- Amazon CloudWatch
- AWS CloudTrail
- AWS Budgets
- AWS Cost Anomaly Detection
- Amazon SNS
