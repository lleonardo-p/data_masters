# ADR-022: Contratos de Dados e Schema de Eventos

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP integra múltiplas fontes e possui fluxo near real-time baseado em eventos. Mudanças não controladas de schema podem quebrar pipelines, gerar indicadores incorretos e dificultar reconciliação.

É necessário formalizar a estrutura mínima dos dados de entrada, especialmente eventos hospitalares simulados.

## Decisão

Será adotada uma estratégia de **contratos de dados** para eventos e datasets críticos.

Todo evento near real-time deverá conter, no mínimo:

- `event_id`;
- `event_type`;
- `schema_version`;
- `event_time`;
- `source_system`;
- localização ou unidade agregada quando aplicável;
- payload sem PII nas etapas posteriores ao processamento de identidade.

Mudanças de schema deverão ser versionadas e validadas antes do processamento.

## Justificativa

Contratos de dados reduzem quebras silenciosas e aumentam confiabilidade entre produtores e consumidores.

A presença de `schema_version`, `event_id` e `event_time` é essencial para validação, idempotência, ordenação lógica e reconciliação.

## Alternativas consideradas

- **Schema livre:** mais flexível, mas aumenta risco de erro em produção.
- **Validação apenas no consumidor final:** detecta problemas tarde demais.
- **Schema Registry completo desde o início:** robusto, mas pode ser excessivo para o MVP.

## Consequências

### Positivas

- Menos quebras em pipelines.
- Melhor comunicação entre produtores e consumidores.
- Suporte a versionamento de eventos.
- Base para governança e qualidade.

### Negativas

- Exige disciplina na evolução de schema.
- Pode reduzir velocidade de mudanças improvisadas.
- Requer validação automatizada nos pipelines.

## Critérios de evolução

Revisar esta decisão se:

- houver múltiplos produtores de eventos;
- schemas mudarem com frequência;
- for necessário suportar compatibilidade backward/forward formal;
- a arquitetura evoluir para Kafka/Kinesis com Schema Registry.

## Referências

- Data Contracts
- Schema Evolution
- Event-Driven Architecture
