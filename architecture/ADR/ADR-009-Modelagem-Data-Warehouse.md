# ADR-009: Modelagem do Data Warehouse Analítico

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa disponibilizar dados analíticos para consultas SQL, dashboards e indicadores de negócio relacionados a arboviroses, clima, eventos ambientais, infraestrutura de saúde e eventos hospitalares simulados.

A camada de consumo precisa ser clara, performática, sem PII e orientada a perguntas analíticas.

## Decisão

A camada **Gold/DW** será modelada com abordagem dimensional, utilizando fatos, dimensões e indicadores agregados.

As tabelas deverão ter grão explícito, nomes padronizados e campos preparados para consumo analítico.

No produto de dengue implementado, `fact_dengue_cases` possui grão de **uma
linha por notificação Silver válida ou com warning**. Medidas 0/1, como
`notification_count`, `confirmed_case_count` e `hospitalized_case_count`, são
aditivas e permitem que Athena ou BI agreguem por data, localidade, demografia e
atributos clínicos sem perder o detalhe.

As dimensões atuais são `dim_date`, `dim_location`, `dim_disease`,
`dim_demographic` e `dim_clinical`. Data e localização exercem múltiplos papéis
na fato.

Novos produtos poderão ter outro grão, desde que ele seja declarado e testado.
O dataset climático diário, por exemplo, termina na Silver enquanto não houver
um consumidor e uma métrica Gold definidos.

O DW não deverá conter CPF, identificadores sensíveis ou dados pessoais diretos. Quando necessário, poderá usar identificadores técnicos pseudonimizados ou agregações sem identificação individual.

## Justificativa

A modelagem dimensional facilita consumo por BI, melhora entendimento dos dados e reduz complexidade para construção de dashboards.

Definir o grão de cada fato evita ambiguidade, duplicidade e erros de agregação. Também permite separar dados detalhados, dimensões de contexto e indicadores consolidados.

A ausência de PII no DW reduz risco de exposição em ferramentas de consumo, consultas SQL e relatórios.

## Alternativas consideradas

- **Consumir diretamente a Silver:** reduz uma etapa de modelagem, mas expõe dados menos preparados e aumenta complexidade no BI.
- **Modelo altamente normalizado:** reduz redundância, mas pode dificultar consultas analíticas e dashboards.
- **Tabelas totalmente agregadas:** simplifica dashboards, mas reduz flexibilidade analítica.
- **Data Warehouse dedicado no Redshift:** pode oferecer performance previsível, mas adiciona custo e complexidade fora do escopo inicial do MVP.

## Consequências

### Positivas

- Melhor organização para consumo analítico.
- Menor complexidade para dashboards.
- Métricas e indicadores mais padronizados.
- Redução de risco de duplicidade por definição de grão.
- Menor exposição de dados sensíveis.
- Base preparada para evolução para Data Mart ou Data Warehouse dedicado.

### Negativas / Trade-offs

- Exige etapa adicional de modelagem.
- Pode gerar duplicidade controlada de dados entre Silver e Gold/DW.
- Requer manutenção de fatos, dimensões e regras de negócio.
- Mudanças em indicadores podem exigir reprocessamento de tabelas Gold/DW.

## Escalabilidade e alternativas

No Athena, escala depende de Parquet, pruning, compactação, views e controle de
bytes por Workgroup. Agregados adicionais só serão criados para consultas
comprovadamente caras ou frequentes.

Redshift será avaliado quando concorrência, latência previsível e workload de BI
justificarem warehouse dedicado. Iceberg resolve necessidades de tabela como
upsert e histórico; não substitui modelagem dimensional nem serving concorrente.

## Critérios de evolução

Esta decisão deve ser revisada se:

- o volume de consultas analíticas crescer significativamente;
- dashboards exigirem baixa latência e alta concorrência;
- houver necessidade de um Data Warehouse dedicado;
- novos domínios exigirem modelos dimensionais específicos;
- indicadores oficiais exigirem versionamento ou governança formal de métricas.

## Referências

- Dimensional Modeling
- Star Schema
- Amazon Athena
- AWS Glue Data Catalog
- Power BI
