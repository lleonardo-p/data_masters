# Caso 2 — Triagem hospitalar near real-time

## Objetivo

Simular eventos de triagem relacionados a dengue, processá-los de forma
assíncrona e disponibilizar indicadores operacionais por API com freshness p95
de até dois minutos.

O case usa dados exclusivamente sintéticos. Identificadores não pertencem a
pessoas reais e não devem ser reutilizados fora do simulador.

## Requisitos

- entrega assíncrona e tolerância a picos;
- processamento pelo menos uma vez com consumidor idempotente;
- isolamento de mensagens que excedam as retentativas;
- PII fora de Silver, Gold, DynamoDB analítico, API, dashboard e logs;
- indicador consultável sob demanda;
- telemetria de latência, erros, duplicidade, backlog e DLQ.

## Evento sintético de entrada

```json
{
  "event_id": "evt_01J...",
  "event_type": "hospital_triage_created",
  "schema_version": "1.0",
  "event_time": "2026-07-18T10:00:00Z",
  "source_system": "hospital_simulator",
  "patient_document": "synthetic-value",
  "municipality_code": "3550308",
  "suspected_disease": "dengue",
  "triage_risk": "moderate"
}
```

O campo identificável existe somente para demonstrar o limite de confiança. Ele
é substituído por `patient_id` no primeiro componente autorizado. O payload
completo não é registrado em logs.

## Arquitetura proposta

```text
Hospital simulator
        |
   API Gateway ou endpoint de ingestão
        |
   SQS Standard --------------------------> SQS DLQ
        |
   Lambda processor
        |-- valida schema e versão
        |-- gera/resolve patient_id em store restrita
        |-- aplica idempotência por event_id
        |-- atualiza indicador condicionalmente
        |-- publica cópia pseudonimizada para Firehose, se necessária
        |
   DynamoDB indicator store
        |
API Gateway -> Lambda query -> dashboard
```

## Por que SQS e Lambda

SQS desacopla o produtor, absorve picos e retém mensagens durante falhas. SQS
Standard pode reenviar mensagens; a idempotência é parte do desenho, não uma
suposição de exactly-once.

Lambda integra o event source mapping, escala consumidores e permite resposta
parcial de lote para repetir apenas mensagens com falha. O `visibility_timeout`
deve ser maior que a janela efetiva de processamento e retentativa.

## Idempotência

Antes de atualizar indicadores, a função cria um item de processamento no
DynamoDB usando escrita condicional:

```text
PK = EVENT#<event_id>
status = processed
expires_at = <TTL>
```

Se a condição indicar que o item já existe, a função reconhece a reentrega sem
somar novamente. O TTL controla apenas retenção do marcador; não é garantia de
expurgo instantâneo.

## Serving e freshness

Indicadores podem usar chaves distribuídas por tempo e geografia, por exemplo:

```text
PK = INDICATOR#DENGUE#UF#SP#2026-07-18
SK = MUNICIPALITY#3550308
```

Uma única chave nacional para todas as atualizações criaria hot partition.
Writes podem ser distribuídos e consolidados para respostas agregadas.

A API responde ao estado atual. O dashboard pode consultar a cada dois minutos.
O SLO é calculado como:

```text
freshness_seconds = available_at - event_time
target: p95 <= 120 seconds
```

Também devem ser medidos p99, idade da mensagem mais antiga, duração Lambda,
throttles, conditional-check failures, DLQ e taxa de erro da API.

## Privacidade e acesso

- somente o componente de identidade acessa o identificador sintético;
- segredo de HMAC fica no Secrets Manager/KMS, não no código;
- `patient_id` é pseudônimo e continua sujeito a controle de acesso;
- não persistir PII direta é preferível quando auditoria não exige o payload;
- se uma Bronze restrita for necessária, aplicar bucket/prefixo isolado,
  criptografia, retenção mínima, auditoria e acesso break-glass;
- não chamar o processo de anonimização enquanto existir reversibilidade ou
  possibilidade de associação.

## Falhas

| Falha | Tratamento |
|---|---|
| Schema inválido | Rejeição controlada ou fila de eventos inválidos com código |
| Falha transitória | Retentativa pelo event source mapping |
| Falha parcial do lote | `ReportBatchItemFailures` |
| Reentrega | Escrita idempotente por `event_id` |
| Poison message | DLQ após `maxReceiveCount` |
| DynamoDB throttling | Backoff, reserved concurrency e revisão da chave |
| API em excesso | Throttling por rota, cache e resposta `429` |

## Escalabilidade e alternativas

- Aumentar concorrência Lambda sem limitar o downstream pode apenas mover o
  gargalo para DynamoDB ou KMS.
- Reserved concurrency e maximum concurrency do event source mapping protegem
  dependências.
- SQS atende o caso enquanto ordenação global e múltiplos consumidores de replay
  não forem requisitos.
- Kinesis é alternativa para ordenação por chave, retenção/replay e múltiplos
  consumidores; MSK/Flink é justificável para ecossistema Kafka ou estado e
  janelas complexas.
- DynamoDB on-demand absorve variação, mas chaves ruins ainda geram hot
  partitions; write sharding é uma evolução possível.
- DynamoDB Global Tables e uma API em outra região exigem roteamento regional,
  estratégia de consistência e resolução de conflitos.

## Critério de pronto

- teste de carga documentado;
- p95 de freshness dentro de 120 segundos;
- reentrega não duplica indicador;
- mensagem inválida chega à DLQ ou fila de inválidos;
- nenhum identificador direto aparece em logs ou resposta;
- dashboard consome a API sem acesso ao DynamoDB;
- alarmes e runbook foram exercitados.

