# ADR-003: Ingestão e Processamento Batch com AWS Glue

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa executar ingestões periódicas de dados públicos, transformar dados entre Bronze, Silver e Gold, enriquecer bases e gerar datasets analíticos.

As cargas podem variar entre extrações simples de APIs e transformações distribuídas com Spark.

## Decisão

O **AWS Glue** será utilizado como principal plataforma de processamento batch e transformação distribuída.

Os jobs Glue Spark serão priorizados para:

- transformação Bronze para Silver;
- geração de Gold e Data Warehouse;
- enriquecimentos com múltiplas fontes;
- deduplicação, padronização, validação e cálculo de indicadores.

Extrações simples de APIs poderão evoluir para **AWS Lambda** ou **Amazon ECS/Fargate** quando o uso de Spark for desnecessário ou caro para cargas pequenas.

## Justificativa

O Glue reduz esforço operacional por ser gerenciado e possuir integração nativa com S3, Glue Catalog, Athena e Spark.

A decisão mantém a arquitetura simples para o MVP, mas evita acoplamento excessivo ao reconhecer que nem toda ingestão precisa de Spark.

## Alternativas consideradas

- **AWS Lambda:** boa para extrações pequenas e eventos, mas limitada para processamento distribuído.
- **Amazon EMR:** mais flexível, porém exige maior operação de cluster.
- **Apache Airflow + Spark:** excelente para orquestração, mas aumenta complexidade operacional.
- **Amazon ECS/Fargate:** útil para workloads containerizados, mas adiciona mais responsabilidade de empacotamento e operação.

## Consequências

### Positivas

- Processamento distribuído gerenciado.
- Integração nativa com o Data Lake.
- Menor esforço operacional.
- Boa aderência ao padrão Lakehouse.

### Negativas

- Tempo de inicialização maior que Lambda.
- Pode ser caro ou excessivo para extrações simples.
- Requer tuning de particionamento, paralelismo e arquivos.

## Critérios de evolução

Revisar esta decisão se:

- extrações simples ficarem caras em Glue;
- pipelines exigirem menor latência;
- houver necessidade de orquestração mais complexa;
- o volume exigir cluster dedicado ou otimizações específicas.

## Referências

- AWS Glue
- Apache Spark
- AWS Glue Best Practices
