# ADR-022: Contratos de Dados e Schema de Eventos

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP recebe dados de múltiplas fontes e possui um fluxo near real-time baseado em eventos hospitalares simulados.

Sem contratos de dados, mudanças de schema podem quebrar pipelines, gerar inconsistências, contaminar camadas analíticas ou dificultar a reconciliação entre batch e near real-time.

## Decisão

Serão definidos contratos de dados para fontes críticas e schemas de eventos para o fluxo near real-time.

Eventos deverão conter campos mínimos como:

- `event_id`;
- `event_type`;
- `schema_version`;
- `event_time`;
- `processing_time`, quando gerado pelo pipeline;
- `source_system`;
- `payload` validado;
- identificador técnico pseudonimizado quando necessário.

O payload não deverá conter CPF ou PII após a etapa de identidade/pseudonimização.

Mudanças compatíveis deverão preservar campos obrigatórios. Mudanças incompatíveis deverão gerar nova versão de schema e validação explícita no pipeline.

Contratos devem definir, quando aplicável:

- campos obrigatórios;
- tipos de dados;
- chaves de negócio;
- regras de nulidade;
- domínios aceitos;
- versão do schema;
- regras de compatibilidade;
- comportamento esperado em caso de quebra de contrato.

## Justificativa

Contratos de dados reduzem risco de quebra silenciosa dos pipelines e aumentam previsibilidade entre produtores e consumidores.

No fluxo near real-time, campos como `event_id`, `event_time` e `schema_version` são essenciais para idempotência, reconciliação, validação e rastreabilidade.

A definição de versionamento permite evoluir os schemas sem interromper consumidores ou misturar eventos incompatíveis.

## Alternativas consideradas

- **Aceitar qualquer schema:** aumenta flexibilidade, mas reduz confiabilidade e dificulta validação.
- **Validar apenas no final do pipeline:** detecta problemas tarde demais e pode contaminar camadas intermediárias.
- **Versionamento informal:** pode funcionar no início, mas dificulta evolução e compatibilidade.
- **Contratos apenas documentais:** úteis para entendimento, mas insuficientes sem validação técnica no pipeline.

## Consequências

### Positivas

- Maior previsibilidade dos pipelines.
- Redução de quebras por mudança de schema.
- Melhor suporte a idempotência e reconciliação.
- Maior rastreabilidade de eventos.
- Base para governança e qualidade de dados.
- Evolução controlada de schemas.

### Negativas / Trade-offs

- Exige manutenção dos contratos.
- Mudanças nas fontes precisam ser versionadas e comunicadas.
- Regras muito rígidas podem bloquear dados válidos em evolução.
- Requer validação técnica nos pipelines.

## Critérios de evolução

Esta decisão deve ser revisada se:

- novas fontes críticas forem adicionadas;
- houver múltiplos produtores de eventos;
- o schema evoluir com frequência;
- dados reais forem processados;
- houver necessidade de schema registry dedicado;
- consumidores externos passarem a depender dos contratos.

## Referências

- Data Contracts
- Schema Versioning
- Event-Driven Architecture
- JSON Schema
- AWS Glue Schema Registry
