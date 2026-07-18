# ADR-006: Mensageria Near Real-Time com Amazon SQS

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui um fluxo near real-time para ingestão de eventos hospitalares simulados, usado para atualizar indicadores recentes com baixa latência.

A solução precisa desacoplar produtores e consumidores, absorver picos, permitir retentativas, controlar falhas e evitar perda de eventos.

O MVP não possui requisito de ordenação estrita, streaming distribuído de alto volume ou processamento com latência de milissegundos.

## Decisão

O **Amazon SQS Standard** será utilizado como serviço de mensageria para o fluxo near real-time.

A fila deverá utilizar:

- Dead Letter Queue (DLQ) para mensagens com falha recorrente;
- política de retry e redrive;
- configuração adequada de visibility timeout;
- alarmes para profundidade da fila e mensagens na DLQ;
- identificador de evento (`event_id`) para suportar idempotência no consumidor.

Como o SQS Standard pode entregar mensagens mais de uma vez, a idempotência será obrigatória no processamento consumidor.

## Justificativa

O SQS é simples, gerenciado, escalável e adequado para desacoplamento entre ingestão e processamento near real-time no escopo do MVP.

A escolha reduz esforço operacional em comparação com soluções de streaming mais complexas, como Kafka ou Kinesis, e atende ao requisito de atualização recente de indicadores sem exigir ordenação global.

A combinação de SQS, Lambda, DLQ e DynamoDB permite construir um fluxo resiliente, com retentativas, tratamento de falhas e controle de duplicidade.

## Alternativas consideradas

- **Amazon Kinesis:** adequado para streaming de alto volume e leitura por múltiplos consumidores, mas adiciona complexidade e custo sem necessidade no MVP.
- **Apache Kafka/MSK:** poderoso para arquiteturas orientadas a eventos, mas exige maior esforço operacional e governança de tópicos, partições e consumidores.
- **EventBridge:** útil para eventos de integração entre sistemas, mas menos adequado para filas de processamento com controle detalhado de retry, DLQ e consumo por lote.
- **Chamada direta para Lambda:** simples, mas acopla produtor e consumidor, reduz controle de retentativas e dificulta absorção de picos.

## Consequências

### Positivas

- Baixo esforço operacional.
- Desacoplamento entre produtor e consumidor.
- Suporte a retry, DLQ e absorção de picos.
- Integração nativa com Lambda e CloudWatch.
- Simplicidade para o MVP.

### Negativas / Trade-offs

- Não garante ordenação global das mensagens.
- Pode entregar mensagens mais de uma vez.
- Exige idempotência no consumidor.
- Não é a melhor opção para streaming analítico de alto volume.
- Pode exigir ajuste fino de visibility timeout e tamanho de lote.

## Escalabilidade e alternativas

A escala acompanha idade da mensagem, profundidade, mensagens em voo, erro e
DLQ. Aumentar consumidores sem limitar concorrência pode pressionar DynamoDB,
KMS e APIs. Visibility timeout, batch size, maximum concurrency e resposta
parcial devem ser testados juntos.

Kinesis será avaliado para retenção/replay, ordenação por chave e múltiplos
consumidores. MSK entra quando compatibilidade Kafka for requisito. Nenhuma
alternativa elimina idempotência e backpressure.

## Critérios de evolução

Esta decisão deve ser revisada se:

- houver necessidade de ordenação por chave;
- o volume de eventos crescer significativamente;
- múltiplos consumidores independentes precisarem ler o mesmo stream;
- houver necessidade de replay amplo de eventos;
- a latência exigida for menor do que a suportada pelo modelo SQS + Lambda;
- o fluxo evoluir para streaming analítico contínuo.

## Referências

- Amazon SQS
- Amazon SQS Dead Letter Queues
- AWS Lambda with SQS
- Amazon CloudWatch Alarms
