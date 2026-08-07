# ADR-003: Processamento do Fluxo Batch

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

O fluxo Batch precisa executar cargas pontuais e backfills sobre milhões de registros de dengue. O processamento deve suportar transformação, validação, enriquecimento, quarentena e modelagem dimensional sem exigir administração de servidores.

## Decisão

Utilizar:

* **AWS Lambda:** extração dos dados da API para a Staging;
* **AWS Glue com PySpark:** processamento entre Bronze, Silver, Quarentena e Gold;
* **AWS Step Functions:** orquestração e controle da sequência dos jobs.

Cada período é extraído separadamente. Após a extração, os jobs processam o lote completo identificado pelo `BATCH_ID`.

## Justificativa

A Lambda é adequada para a extração por período e permite transferir os dados por streaming, sem carregar todo o arquivo em memória.

O AWS Glue oferece processamento distribuído e integração direta com Amazon S3 e Glue Data Catalog. A Step Functions centraliza a ordem das etapas, as tentativas, as falhas e a rastreabilidade da execução.

## Alternativas

* **Executar todo o fluxo em AWS Lambda:** não adotado devido aos limites de duração, memória e armazenamento temporário.
* **Amazon EMR:** não adotado por exigir maior configuração e administração para a carga atual.
* **Amazon ECS com Fargate:** tecnicamente viável, mas não adotado por aumentar o esforço de empacotamento, execução e monitoramento.
* **Processamento local:** não adotado por limitar escalabilidade, disponibilidade e reprodutibilidade.
