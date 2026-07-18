# ADR-003: Processamento Batch com AWS Glue

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa processar dados de múltiplas fontes em fluxo batch, incluindo dados de saúde pública, clima, eventos ambientais, infraestrutura de saúde e bases de apoio.

O processamento deve suportar extração, padronização, validação, enriquecimento, deduplicação, criação de camadas Silver e Gold, reprocessamento histórico e execução diária.

Como o projeto está em fase de MVP, a solução deve reduzir esforço operacional e permitir execução escalável sem necessidade de administrar clusters manualmente.

## Decisão

O **AWS Glue** será adotado como motor principal para processamento batch distribuído.

O Glue será utilizado principalmente para:

- transformar dados da Bronze para Silver;
- construir datasets analíticos na Gold/DW;
- executar validações e regras de qualidade em lote;
- realizar enriquecimentos entre fontes;
- executar cargas históricas e backfills parametrizados;
- integrar dados processados com Glue Data Catalog e Athena.

Extrações simples de APIs poderão ser executadas por **AWS Lambda** ou **ECS/Fargate**, quando o uso de Spark for desnecessário. Essas extrações deverão gravar os dados na Staging ou Bronze para posterior processamento pelo pipeline batch.

## Justificativa

O AWS Glue reduz esforço operacional por oferecer processamento gerenciado baseado em Spark, integração nativa com Amazon S3, Glue Data Catalog, Athena, CloudWatch e IAM.

A escolha favorece o MVP porque evita a necessidade de provisionar e administrar clusters, acelera a implementação e permite processar volumes maiores caso o projeto cresça.

Separar extrações simples do processamento distribuído evita uso excessivo de Glue para tarefas pequenas, reduzindo custo e complexidade.

## Alternativas consideradas

- **Amazon EMR:** oferece maior controle sobre clusters e configurações Spark, mas aumenta esforço operacional e complexidade para o MVP.
- **Lambda para todo o batch:** simples para tarefas pequenas, mas limitado para processamento distribuído, grandes volumes e transformações analíticas complexas.
- **ECS/Fargate para todo o batch:** flexível para execução conteinerizada, mas exigiria mais desenho operacional para agendamento, logs, escalabilidade e dependências.
- **Databricks:** forte para Lakehouse e Spark gerenciado, mas adicionaria custo e complexidade fora do escopo AWS serverless do MVP.
- **Processamento local:** simples para protótipo, mas não representa uma arquitetura cloud escalável.

## Consequências

### Positivas

- Processamento distribuído gerenciado.
- Integração nativa com S3, Glue Data Catalog, Athena e CloudWatch.
- Menor esforço operacional em relação à administração de clusters.
- Suporte a backfill e reprocessamento histórico.
- Boa aderência ao modelo Medallion.
- Possibilidade de evolução para cargas maiores.

### Negativas / Trade-offs

- Pode ter custo desnecessário se usado para tarefas simples.
- Exige atenção a particionamento, compactação e small files.
- Jobs Spark podem demandar tuning de memória, paralelismo e shuffle.
- Não é a melhor opção para eventos de baixa latência ou processamento evento a evento.

## Escalabilidade e alternativas

A primeira ação será habilitar Glue Auto Scaling com máximo controlado e medir
`DPUSeconds`, duração, skew, shuffle, spill e tamanho dos arquivos. Jobs e
backfills devem receber partições como parâmetro para evitar reprocessamento
integral.

EMR será avaliado por benchmark para workloads longos/contínuos, runtime ou
bibliotecas específicas, cluster persistente, tuning indisponível no Glue ou
economia comprovada. EMR amplia controle e responsabilidade operacional. Para
APIs, Lambda atende extrações curtas; Fargate atende duração superior a 15
minutos, dependências pesadas e fan-out limitado pelo fornecedor.

## Critérios de evolução

Esta decisão deve ser revisada se:

- o custo dos jobs Glue crescer acima do previsto;
- os tempos de execução exigirem tuning avançado ou clusters dedicados;
- o volume de dados exigir maior controle de infraestrutura;
- houver necessidade de streaming distribuído;
- a arquitetura evoluir para uma plataforma Lakehouse com Apache Iceberg, Hudi ou Delta Lake em escala produtiva.

## Referências

- AWS Glue
- AWS Glue Jobs
- AWS Glue Data Catalog
- Amazon Athena
- AWS CloudWatch
