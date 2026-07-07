# ADR-018: Reconciliação entre Batch e Near Real-Time

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui dois fluxos de dados complementares:

- fluxo batch, responsável pela consolidação oficial dos dados analíticos;
- fluxo near real-time, responsável por atualizar indicadores recentes com menor latência.

Sem uma regra clara de reconciliação, o mesmo evento pode ser contado duas vezes ou indicadores temporários podem divergir da visão oficial.

## Decisão

A arquitetura adotará uma estratégia de reconciliação entre batch e near real-time.

O fluxo near real-time será tratado como visão operacional recente. O fluxo batch será tratado como fonte oficial consolidada para indicadores históricos e analíticos.

A reconciliação deverá usar campos como:

- `event_id`;
- `event_time`;
- `processing_time`;
- `source_system`;
- `schema_version`;
- janela de referência;
- status de processamento.

Após a consolidação batch oficial de uma janela, os indicadores near real-time da mesma janela deverão ser substituídos, reconciliados ou marcados como não oficiais.

O batch terá precedência sobre a visão near real-time quando houver divergência entre os dados consolidados e os indicadores temporários.

## Justificativa

O fluxo near real-time entrega rapidez, mas pode conter eventos atrasados, duplicados, inválidos ou ainda não reconciliados.

O batch permite processar a janela completa, aplicar validações mais robustas, deduplicar, enriquecer e consolidar dados com maior confiabilidade.

Definir precedência do batch evita dupla contagem e deixa claro para consumidores que a visão NRT é operacional e provisória.

## Alternativas consideradas

- **Usar apenas batch:** simplifica a arquitetura, mas não atende à necessidade de indicadores recentes.
- **Usar apenas near real-time:** reduz latência, mas aumenta risco de inconsistência e dificulta auditoria histórica.
- **Somar batch e near real-time sem reconciliação:** simples, mas pode gerar dupla contagem.
- **Manter indicadores separados sem regra de precedência:** reduz acoplamento, mas cria ambiguidade para consumidores.

## Consequências

### Positivas

- Redução de risco de dupla contagem.
- Separação clara entre visão operacional e visão oficial.
- Maior confiabilidade dos indicadores consolidados.
- Suporte a eventos atrasados e reprocessamento.
- Melhor rastreabilidade por `event_id` e janelas de referência.

### Negativas / Trade-offs

- Aumenta complexidade de modelagem e processamento.
- Exige controle de estado entre NRT e batch.
- Pode haver divergência temporária entre dashboard recente e dados consolidados.
- Requer comunicação clara sobre o significado dos indicadores provisórios.

## Critérios de evolução

Esta decisão deve ser revisada se:

- a latência do batch precisar ser reduzida significativamente;
- a visão near real-time passar a ser considerada oficial;
- houver necessidade de processamento streaming com garantia mais forte de consistência;
- o volume de eventos atrasados crescer;
- a lógica de reconciliação se tornar complexa demais para o modelo atual.

## Referências

- Lambda Architecture
- Idempotent Event Processing
- Event Time vs Processing Time
- Amazon DynamoDB
- Amazon S3
