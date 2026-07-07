# ADR-009: Modelagem do Data Warehouse Analítico

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa disponibilizar indicadores consolidados para análise epidemiológica, operacional e territorial.

A camada Gold deve ser consumida por dashboards e consultas SQL, exigindo clareza de grão, dimensões, fatos e métricas.

## Decisão

A camada analítica será modelada em formato dimensional, com **tabelas fato e dimensões**.

Exemplos de entidades:

- fatos de casos, notificações, internações e indicadores climáticos;
- dimensões de tempo, município, UF, doença, fonte de dados e infraestrutura de saúde;
- métricas como incidência, letalidade, hospitalização, tempo de notificação e capacidade assistencial.

Dados pessoais não devem estar presentes no DW. Qualquer análise de paciente deve ser agregada ou pseudonimizada de forma controlada.

## Justificativa

Modelagem dimensional facilita consumo analítico, reduz complexidade para BI e torna os indicadores mais compreensíveis.

A definição explícita de grão e regra de cálculo evita ambiguidades nos KPIs/indicadores.

## Alternativas consideradas

- **Modelo altamente normalizado:** útil para sistemas transacionais, mas menos eficiente para BI.
- **Data Vault:** robusto para auditoria histórica, mas excessivo para o escopo atual.
- **Tabelas flat sem modelagem:** simples no início, mas tendem a gerar duplicidade e inconsistência de métricas.

## Consequências

### Positivas

- Consumo analítico mais simples.
- Métricas padronizadas.
- Melhor performance para dashboards.
- Separação entre dado tratado e dado de negócio.

### Negativas

- Exige manutenção de dimensões e regras de negócio.
- Pode gerar duplicidade se o grão não for bem definido.
- Mudanças de regra exigem versionamento e reprocessamento.

## Critérios de evolução

Revisar esta decisão se:

- houver muitas mudanças históricas em dimensões;
- surgirem múltiplos domínios com regras complexas;
- houver necessidade de rastreabilidade histórica mais forte;
- o consumo analítico exigir um engine dedicado como Redshift.

## Referências

- Dimensional Modeling
- Star Schema
- Kimball Data Warehouse Toolkit
