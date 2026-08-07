# ADR-015: Formatos de Arquivo e Particionamento

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

O fluxo Batch precisa armazenar os dados extraídos com rastreabilidade e disponibilizar as camadas processadas em um formato eficiente para AWS Glue e Amazon Athena.

O layout também deve separar execuções, permitir reprocessamentos e identificar quando cada conjunto de dados foi produzido.

## Decisão

Utilizar os seguintes formatos:

* **Staging:** JSON Lines compactado com Gzip (`.jsonl.gz`);
* **Bronze, Silver, Quarentena e Gold:** Apache Parquet com compressão Snappy.

As camadas de processamento são organizadas pela data lógica da execução:

```text
processing_date=YYYY-MM-DD/granularity=day|month/
```

Na Staging, o período solicitado também faz parte do caminho:

```text
processing_date=YYYY-MM-DD/
granularity=day|month/
reference_period=YYYY-MM-DD|YYYY-MM/
```

O `reference_period` e o `batch_id` permanecem como metadados nos registros processados.

A Gold é organizada por tabela fato e dimensões e representa o snapshot analítico mais recente.

## Justificativa

### JSONL com Gzip

O JSONL mantém um objeto JSON independente por linha, permitindo que a Lambda transfira a resposta da API por streaming sem carregar todo o conteúdo em memória.

A compressão Gzip reduz o volume transferido e armazenado. Esse formato é adequado para a Staging, onde a prioridade é preservar o conteúdo extraído.

### Parquet com Snappy

O Parquet é colunar e permite que Glue e Athena leiam apenas as colunas necessárias. Ele também preserva tipos, reduz o volume examinado e melhora consultas analíticas.

O Snappy foi escolhido por oferecer descompressão rápida e baixo consumo de CPU. Ele comprime menos que o Gzip, mas apresenta melhor equilíbrio para operações frequentes de leitura e transformação.

### Data de processamento

O particionamento por `processing_date`:

* separa as execuções do pipeline;
* facilita auditoria e rastreabilidade;
* evita mistura entre lotes;
* permite localizar e reprocessar uma execução;
* mantém o período dos dados independente da data em que foram processados.

A data de processamento representa quando o lote foi executado. O período de referência representa quais notificações foram solicitadas à API.

## Alternativas

* **CSV:** não adotado porque não preserva tipos, ocupa mais espaço e exige interpretação adicional durante a leitura.
* **JSON sem compressão:** não adotado devido ao maior volume de armazenamento e transferência.
* **JSONL em todas as camadas:** não adotado porque é menos eficiente para consultas analíticas.
* **Apache Avro:** não adotado porque seu formato orientado a linhas é mais adequado a eventos do que às agregações do Athena.
* **Apache ORC:** tecnicamente viável, mas não adotado porque o Parquet possui ampla integração com os componentes utilizados.
* **Parquet com Gzip:** não adotado porque economizaria mais espaço, mas aumentaria o custo de CPU durante leituras e transformações.
* **Apache Iceberg, Delta Lake ou Apache Hudi:** não adotados porque controle transacional, versionamento e operações de `MERGE` aumentariam a complexidade sem necessidade para o snapshot atual.
* **Particionamento pela data de notificação:** não adotado como partição principal porque uma mesma execução pode processar diferentes períodos e precisa permanecer rastreável como um único lote.
