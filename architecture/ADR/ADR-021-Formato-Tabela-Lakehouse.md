# ADR-021: Formato de Tabela Lakehouse

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP armazena dados em S3 e usa Parquet nas camadas tratadas e analíticas. Essa abordagem é suficiente para o MVP, mas pode se tornar limitada quando houver necessidade de updates, deletes, time travel, schema evolution e maior controle transacional.

## Decisão

Para o MVP, as tabelas Silver, Gold e DW serão armazenadas em **Parquet particionado**.

Para evolução produtiva, será considerada a adoção de **Apache Iceberg** nas tabelas críticas da Silver e Gold.

A adoção de Iceberg deve ser priorizada para tabelas que exigirem:

- upserts;
- correções históricas;
- late arriving data;
- schema evolution;
- time travel;
- controle transacional no Data Lake.

## Justificativa

Parquet é simples, barato e suficiente para o estágio inicial. Iceberg adiciona recursos avançados de Lakehouse, mas aumenta complexidade e exige governança mais madura.

## Alternativas consideradas

- **Parquet puro:** selecionado para o MVP por simplicidade.
- **Apache Iceberg:** recomendado para evolução produtiva.
- **Delta Lake:** forte opção Lakehouse, mas menos nativa no ecossistema AWS serverless do projeto.
- **Apache Hudi:** bom para upserts, mas adiciona complexidade operacional.

## Consequências

### Positivas

- MVP simples e econômico.
- Caminho claro para Lakehouse transacional.
- Melhor suporte futuro a reconciliação e correção histórica.

### Negativas

- Parquet puro exige reprocessamentos mais manuais.
- Iceberg adiciona complexidade de catálogo, manutenção e operação.
- A migração precisa ser planejada para evitar quebra de consumidores.

## Critérios de evolução

Migrar tabelas críticas para Iceberg quando:

- houver muitas correções históricas;
- a reconciliação batch/NRT exigir upsert frequente;
- o custo de reprocessar partições inteiras ficar alto;
- consumidores exigirem versionamento e time travel.

## Referências

- Apache Parquet
- Apache Iceberg
- AWS Glue Data Catalog
- Amazon Athena Iceberg Tables
