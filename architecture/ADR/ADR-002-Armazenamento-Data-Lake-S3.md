# ADR-002: Arquitetura do Data Lake

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

O fluxo Batch precisa armazenar milhões de registros históricos de dengue com baixo custo, rastreabilidade e possibilidade de reprocessamento. Os dados também devem ser tratados progressivamente até ficarem disponíveis para análise.

## Decisão

Utilizar o Amazon S3 como Data Lake, organizado nas seguintes camadas:

* **Staging:** preserva os arquivos extraídos da API;
* **Bronze:** converte os dados para Parquet e adiciona metadados do lote;
* **Silver:** valida, padroniza, enriquece e remove duplicidades;
* **Quarentena:** isola registros que não atendem às regras obrigatórias;
* **Gold:** disponibiliza fatos e dimensões para consumo analítico.

## Justificativa

O Amazon S3 oferece armazenamento escalável, durável e com baixo esforço operacional. A separação em camadas facilita auditoria, reprocessamento, aplicação de regras de qualidade e identificação da origem dos dados.

A arquitetura também se integra diretamente ao AWS Glue, Glue Data Catalog e Amazon Athena.

## Alternativas

* **Banco de dados relacional:** não adotado devido ao custo e à necessidade de dimensionar infraestrutura para o volume histórico.
* **Camada única no Amazon S3:** não adotada porque dificultaria a rastreabilidade, o reprocessamento e a separação entre dados brutos, tratados e analíticos.
* **Data Lakehouse:** não adotado porque os recursos adicionais de gerenciamento transacional não são necessários para o processo atual. Sua implementação aumentaria o tempo e o custo de desenvolvimento do MVP.
* **Data warehouse dedicado:** não adotado devido ao maior custo e à complexidade desnecessária para a carga atual.
