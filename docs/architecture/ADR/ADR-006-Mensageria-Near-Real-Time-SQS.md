# ADR-006: Mensageria Near Real-Time com Amazon SQS

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui um fluxo near real-time para eventos hospitalares simulados, como notificações de triagem ou suspeita de arbovirose.

Esses eventos precisam ser desacoplados do processamento consumidor, tolerantes a falhas e processados com baixo custo.

## Decisão

Será utilizado **Amazon SQS Standard** como fila de mensageria para o fluxo near real-time.

A fila deverá possuir:

- DLQ para mensagens com falha recorrente;
- controle de `visibility timeout`;
- política de retry e redrive;
- idempotência baseada em `event_id`;
- contrato mínimo de evento;
- alarmes para idade da mensagem, mensagens na DLQ e crescimento anormal da fila.

## Justificativa

SQS é simples, barato, gerenciado e suficiente para o fluxo proposto. Ele desacopla produtor e consumidor sem exigir operação de clusters ou brokers.

Como o projeto não exige ordering estrito nem throughput massivo no MVP, SQS Standard é mais adequado do que alternativas mais complexas.

## Alternativas consideradas

- **Amazon Kinesis:** melhor para alto throughput e streaming contínuo, mas adiciona custo e complexidade.
- **Apache Kafka/MSK:** robusto para streaming corporativo, mas excessivo para o MVP.
- **EventBridge:** bom para eventos de integração, mas menos adequado como fila principal de processamento com retry e DLQ neste caso.
- **SQS FIFO:** útil quando ordering estrito é necessário, mas com menor throughput e maior restrição operacional.

## Consequências

### Positivas

- Baixo custo e baixa operação.
- Desacoplamento entre produtor e processador.
- Resiliência via retry e DLQ.
- Escalabilidade automática para o escopo do MVP.

### Negativas

- Entrega pode ser duplicada.
- Não garante ordem global dos eventos.
- Exige idempotência no consumidor.

## Critérios de evolução

Revisar esta decisão se:

- houver necessidade de ordering estrito;
- o volume de eventos crescer muito;
- múltiplos consumidores precisarem ler o mesmo stream independentemente;
- houver necessidade de replay estruturado de eventos.

## Referências

- Amazon SQS
- AWS Lambda with SQS
- Dead-letter queues
