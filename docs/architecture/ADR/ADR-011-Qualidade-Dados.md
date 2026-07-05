# ADR-011: Qualidade de Dados e Quarentena

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP integra dados de diferentes fontes, com formatos, granularidades e níveis de confiabilidade distintos.

Erros de schema, duplicidade, valores nulos, datas inválidas e inconsistências de domínio podem impactar diretamente indicadores epidemiológicos.

## Decisão

A qualidade de dados será aplicada nos pipelines batch e near real-time com regras classificadas por severidade:

- **Bloqueante:** impede avanço da carga.
- **Quarentena:** isola registros inválidos para análise posterior.
- **Alerta:** registra anomalia sem interromper o pipeline.

As regras mínimas incluem:

- validação de schema;
- obrigatoriedade de chaves e datas;
- ausência de PII nas camadas analíticas;
- checagem de duplicidade;
- validação de domínios, UF, município e doença;
- controles de volumetria e freshness.

## Justificativa

Qualidade de dados precisa ser parte do pipeline, não uma análise manual posterior.

A classificação por severidade evita que problemas pequenos parem todo o fluxo, mas impede que erros críticos contaminem as camadas Silver, Gold e DW.

## Alternativas consideradas

- **Sem validação formal:** reduz esforço inicial, mas aumenta risco de indicadores incorretos.
- **Validação apenas no dashboard:** identifica problemas tarde demais.
- **Framework externo completo:** pode ser útil, mas aumenta escopo do MVP.

## Consequências

### Positivas

- Maior confiança nos indicadores.
- Rastreabilidade de registros inválidos.
- Prevenção de propagação de erro entre camadas.
- Melhor governança e operação.

### Negativas

- Maior esforço de desenvolvimento.
- Necessidade de manter regras por fonte.
- Risco de bloqueios excessivos se regras forem muito rígidas.

## Critérios de evolução

Revisar esta decisão se:

- novas fontes aumentarem a complexidade das regras;
- houver necessidade de score formal de qualidade;
- consumidores exigirem SLAs de qualidade;
- regras passarem a ser gerenciadas por time de governança.

## Referências

- AWS Glue Data Quality
- Data Quality Dimensions
- Great Expectations
