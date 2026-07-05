# ADR-018: Reconciliação entre Batch e Near Real-Time

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP combina dados oficiais processados em batch com eventos near real-time simulados.

Sem uma estratégia de reconciliação, o mesmo evento pode ser contado duas vezes ou indicadores recentes podem divergir dos dados oficiais consolidados.

## Decisão

A reconciliação será baseada em:

- `event_id` para idempotência;
- `event_time` e `processing_time` para controle temporal;
- watermark por fonte e janela de consolidação;
- prioridade do batch oficial para dados consolidados;
- atualização ou descarte controlado de eventos near real-time após consolidação;
- trilha de divergências para auditoria.

O near real-time deve ser tratado como visão operacional recente. A visão oficial e histórica deve vir da camada Gold/DW consolidada.

## Justificativa

A separação entre visão operacional e visão oficial evita inconsistência de indicadores.

Watermark e idempotência permitem lidar com eventos atrasados, duplicados e reprocessamentos sem comprometer a confiança analítica.

## Alternativas consideradas

- **Somar batch e near real-time diretamente:** rejeitado por risco de dupla contagem.
- **Usar apenas batch:** reduz complexidade, mas perde visão recente.
- **Usar apenas near real-time:** não substitui dados oficiais e consolidados.
- **Reprocessar tudo sempre:** simples conceitualmente, mas caro e ineficiente.

## Consequências

### Positivas

- Evita dupla contagem.
- Mantém visão recente e visão oficial separadas.
- Melhora confiança nos indicadores.
- Permite reprocessamento controlado.

### Negativas

- Aumenta complexidade de regras.
- Exige controle de watermark e idempotência.
- Pode haver divergência temporária entre painéis recentes e consolidados.

## Critérios de evolução

Revisar esta decisão se:

- eventos atrasados forem frequentes;
- o volume near real-time crescer muito;
- houver necessidade de correção histórica em larga escala;
- a arquitetura evoluir para tabelas transacionais como Apache Iceberg.

## Referências

- Idempotent Data Pipelines
- Watermarking
- Event Time vs Processing Time
