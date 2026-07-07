# ADR-021: Uso de Parquet no MVP e Evolução para Apache Iceberg

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa armazenar dados analíticos no Data Lake em formato eficiente para consulta SQL, processamento batch e consumo por BI.

No MVP, o foco é simplicidade, baixo custo e menor complexidade operacional. Porém, algumas necessidades futuras podem exigir recursos transacionais no Data Lake, como updates, deletes, schema evolution e time travel.

## Decisão

No MVP, as camadas Silver, Gold e DW utilizarão **arquivos Parquet particionados** no Amazon S3.

Formatos transacionais de tabela, como **Apache Iceberg**, não serão adotados inicialmente.

O Apache Iceberg será considerado como evolução futura para tabelas críticas que precisem de:

- updates e deletes frequentes;
- correções históricas;
- time travel;
- evolução de schema com maior controle;
- tratamento recorrente de late arriving data;
- transações ACID no Data Lake;
- melhor gerenciamento de metadados e compactação.

## Justificativa

Parquet atende bem ao MVP por ser colunar, eficiente para consultas analíticas, integrado ao Glue, Athena e Spark, e mais simples de operar.

Adotar Iceberg desde o início adicionaria complexidade de catálogo, configuração, manutenção de metadados e boas práticas operacionais que ainda não são necessárias para o escopo atual.

A decisão mantém a arquitetura simples no MVP, mas preserva caminho claro de evolução para um padrão Lakehouse mais robusto.

## Alternativas consideradas

- **Apache Iceberg desde o início:** oferece recursos avançados, mas aumenta complexidade sem necessidade imediata.
- **Delta Lake:** forte para Lakehouse, mas possui melhor aderência em stacks como Databricks e exigiria avaliação adicional no contexto Athena/Glue.
- **Apache Hudi:** adequado para upserts e ingestões incrementais, mas adiciona complexidade operacional.
- **CSV/JSON em camadas analíticas:** simples, mas menos eficiente para consulta e armazenamento analítico.

## Consequências

### Positivas

- Menor complexidade no MVP.
- Boa performance analítica com Parquet.
- Integração simples com Glue, Athena e S3.
- Menor curva operacional.
- Caminho claro para evolução Lakehouse.

### Negativas / Trade-offs

- Updates, deletes e time travel não são suportados nativamente em arquivos Parquet simples.
- Correções históricas podem exigir reprocessamento de partições.
- Evolução de schema precisa ser controlada com cuidado.
- Late arriving data pode exigir estratégias específicas de reprocessamento.

## Critérios de evolução

Esta decisão deve ser revisada se:

- updates e deletes se tornarem frequentes;
- houver necessidade de time travel;
- correções históricas forem recorrentes;
- late arriving data impactar significativamente as tabelas analíticas;
- o volume de dados exigir otimização avançada de metadados;
- a arquitetura evoluir para Lakehouse produtivo.

## Referências

- Apache Parquet
- Apache Iceberg
- Amazon Athena Iceberg Tables
- AWS Glue Data Catalog
- Lakehouse Architecture
