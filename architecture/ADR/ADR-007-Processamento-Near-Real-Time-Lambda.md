# ADR-007: Processamento Near Real-Time com AWS Lambda

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa processar eventos hospitalares simulados em near real-time para atualizar indicadores recentes, sem aguardar o ciclo batch diário.

O processamento deve ser simples, escalável, de baixo esforço operacional, integrado ao SQS e capaz de aplicar validações, idempotência e atualização em uma store de baixa latência.

## Decisão

O **AWS Lambda** será utilizado como consumidor dos eventos da fila SQS no fluxo near real-time.

A função Lambda deverá:

- consumir mensagens da fila SQS;
- validar contrato e schema do evento;
- rejeitar ou direcionar mensagens inválidas conforme regra de qualidade;
- aplicar idempotência com base em `event_id`;
- atualizar indicadores ou estados recentes no DynamoDB;
- evitar gravação evento a evento no S3 para não gerar small files;
- não registrar PII, CPF ou payload sensível em logs;
- tratar falhas por mensagem, evitando reprocessar todo o lote quando apenas um evento falhar.

## Justificativa

Lambda é adequado para processamento orientado a eventos com baixa latência operacional, integração nativa com SQS, escalabilidade automática e baixo esforço de infraestrutura.

Para o MVP, Lambda reduz a complexidade em comparação com serviços de streaming ou clusters dedicados. O uso combinado com DynamoDB permite atualização rápida de indicadores near real-time sem impactar a camada analítica oficial baseada em S3, Gold e DW.

Evitar escrita evento a evento no S3 reduz risco de pequenos arquivos e preserva o Data Lake para o fluxo batch consolidado.

## Alternativas consideradas

- **AWS Glue Streaming:** adequado para streaming distribuído, mas mais complexo e custoso para o volume e escopo do MVP.
- **Kinesis Data Analytics/Flink:** indicado para processamento contínuo de streams complexos, mas excessivo para o caso atual.
- **ECS/Fargate Worker:** oferece mais controle, mas exige mais configuração operacional para escala, deploy e monitoramento.
- **Processar tudo no batch:** simplifica a arquitetura, mas não atende à necessidade de indicadores recentes.

## Consequências

### Positivas

- Baixa complexidade operacional.
- Escalabilidade automática.
- Integração nativa com SQS, DynamoDB e CloudWatch.
- Boa aderência ao MVP near real-time.
- Redução de small files no S3.
- Isolamento entre visão operacional recente e visão analítica oficial.

### Negativas / Trade-offs

- Limites de tempo de execução e memória da Lambda.
- Necessidade de idempotência para lidar com reentrega de mensagens.
- Pode exigir controle de concorrência para evitar pressão no DynamoDB.
- Não é ideal para processamento streaming complexo ou de alto volume.
- Falhas parciais precisam ser tratadas corretamente para evitar reprocessamento desnecessário.

## Critérios de evolução

Esta decisão deve ser revisada se:

- o volume de eventos crescer significativamente;
- a lógica de processamento se tornar complexa demais para Lambda;
- houver necessidade de janelas, agregações contínuas ou processamento stateful;
- a latência ou throughput exigirem outro mecanismo de streaming;
- o custo por invocação crescer acima do previsto.

## Referências

- AWS Lambda
- AWS Lambda with Amazon SQS
- AWS Lambda Partial Batch Response
- Amazon DynamoDB
- Amazon CloudWatch
