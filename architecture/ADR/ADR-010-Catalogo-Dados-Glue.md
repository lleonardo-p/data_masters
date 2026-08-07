# ADR-010: Catálogo de Dados com AWS Glue Data Catalog

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

Os arquivos Parquet da camada Gold precisam ser apresentados como tabelas para consultas no Amazon Athena. O catálogo deve registrar schemas, formatos, localizações e partições sem copiar os dados armazenados no Amazon S3.

## Decisão

Utilizar o AWS Glue Data Catalog como catálogo técnico da camada Gold.

Após a aprovação da reconciliação, a Step Functions:

1. inicia o AWS Glue Crawler;
2. aguarda a conclusão da execução;
3. atualiza as tabelas e partições no banco `baip_dev_gold`;
4. finaliza o pipeline somente após o sucesso do Crawler.

O Crawler examina apenas a camada Gold validada.

## Justificativa

O Glue Data Catalog oferece um catálogo gerenciado e compartilhado entre AWS Glue e Amazon Athena.

O Crawler reduz a necessidade de cadastrar manualmente tabelas e partições a cada processamento. Sua execução após a reconciliação evita disponibilizar no catálogo um lote que não passou pelas verificações de qualidade.

## Alternativas

* **Criação manual de tabelas no Athena:** não adotada porque exigiria manutenção dos schemas e das partições a cada alteração.
* **Tabelas declaradas integralmente com Terraform:** ofereceriam maior controle do schema, mas aumentariam a manutenção da infraestrutura para cada evolução do modelo.
* **Hive Metastore próprio:** não adotado devido à necessidade de provisionamento, disponibilidade, atualização e monitoramento do serviço.
* **Consulta direta aos caminhos do Amazon S3:** não adotada porque dificultaria a descoberta, padronização e reutilização dos conjuntos de dados.
* **AWS Lake Formation:** não adotado no MVP porque seus controles avançados de governança e acesso granular não são necessários para o consumo atual.
