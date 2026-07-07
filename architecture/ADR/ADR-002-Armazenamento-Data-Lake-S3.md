# ADR-002: Armazenamento do Data Lake no Amazon S3

* **Status:** Aceito
* **Data:** 2026-07-07
* **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP (Brazil Arbovirus Intelligence Platform) precisa armazenar dados de múltiplas fontes.

A solução deve suportar dados temporários de ingestão, dados brutos, dados tratados e dados analíticos, mantendo baixo custo, rastreabilidade, reprocessamento, auditoria, particionamento, integração com catálogo e consulta SQL.

## Decisão

O **Amazon S3** será a camada principal de armazenamento do Data Lake.

Os dados serão organizados em uma arquitetura baseada em camadas:

* **Staging:** área temporária de aterrissagem dos dados ingeridos, usada para validações iniciais, controle técnico da ingestão e preparação antes da persistência na Bronze.
* **Bronze:** dados brutos persistidos, preservados no formato original ou semi-original, mantendo rastreabilidade da origem.
* **Silver:** dados tratados, padronizados, deduplicados, enriquecidos e pseudonimizados quando necessário.
* **Gold:** dados analíticos, agregações, fatos, dimensões e indicadores para consumo.

A área **Staging** terá retenção curta e será limpa automaticamente após **7 dias**.

As demais camadas do Data Lake deverão possuir políticas de **retenção**, **expurgo** e **lifecycle**, definidas conforme a natureza dos dados, necessidade de auditoria, custo de armazenamento e requisitos de reprocessamento.

O Data Lake deverá utilizar criptografia, bloqueio de acesso público, controle de permissões, versionamento quando aplicável e políticas de lifecycle.

## Justificativa

O Amazon S3 foi escolhido por ser um serviço escalável, durável, flexível e de baixo custo para armazenamento de dados em diferentes formatos e estágios de processamento.

O S3 também possui integração nativa com serviços analíticos e de governança da AWS, como AWS Glue, Glue Data Catalog, Amazon Athena e AWS Lake Formation.

A separação entre Staging, Bronze, Silver e Gold permite organizar melhor o ciclo de vida dos dados. A Staging reduz acoplamento entre ingestão e persistência, enquanto Bronze, Silver e Gold mantêm uma estrutura clara para rastreabilidade, tratamento, enriquecimento e consumo analítico.

A política de exclusão da Staging após 7 dias evita acúmulo de arquivos temporários e reduz custo operacional. Já as políticas de retenção e expurgo nas demais camadas permitem controlar o ciclo de vida dos dados de acordo com requisitos técnicos, analíticos e regulatórios.

## Alternativas consideradas

* **Amazon Redshift:** adequado para Data Warehouse e consultas analíticas de alta performance, mas menos flexível como armazenamento principal de dados brutos e históricos em múltiplos formatos.
* **Amazon RDS/PostgreSQL:** adequado para dados relacionais e transacionais, mas limitado para armazenar grandes volumes de dados brutos, semi-estruturados e históricos em uma arquitetura de Data Lake.
* **Amazon DynamoDB:** adequado para acesso de baixa latência e indicadores near real-time, mas não para armazenar o histórico analítico completo do Data Lake.
* **Armazenamento local/on-premises:** oferece maior controle físico da infraestrutura, porém aumenta o esforço operacional, reduz elasticidade e dificulta a integração com serviços analíticos gerenciados.

## Consequências

### Positivas

* Baixo custo de armazenamento.
* Escalabilidade e alta durabilidade.
* Separação clara entre dados temporários, brutos, tratados e analíticos.
* Suporte a reprocessamento, auditoria e rastreabilidade.
* Integração com serviços analíticos e catálogo de dados.
* Possibilidade de evolução para padrões de Lakehouse.
* Redução de acúmulo de dados temporários por meio de limpeza automática da Staging.

### Negativas / Trade-offs

* Exige governança clara de buckets, prefixes, permissões e particionamento.
* Pode gerar problema de pequenos arquivos se a ingestão e o processamento forem mal projetados.
* Depende de catálogo para consultas estruturadas via SQL.
* Exige definição cuidadosa de políticas de retenção, expurgo e lifecycle.
* Dados armazenados em S3 não oferecem, por padrão, controle transacional como um banco relacional.

## Critérios de evolução

Esta decisão deve ser revisada se:

* as tabelas Silver ou Gold exigirem updates, deletes e time travel frequentes;
* houver necessidade de transações ACID diretamente no Data Lake;
* o volume de dados exigir otimização avançada de layout e compactação;
* consultas analíticas exigirem performance previsível de um Data Warehouse dedicado;
* houver requisitos regulatórios mais rígidos de retenção, expurgo ou isolamento de dados;
* a arquitetura evoluir para um modelo Lakehouse com formatos transacionais como Apache Iceberg, Apache Hudi ou Delta Lake.

## Referências

* Amazon S3
* AWS Glue Data Catalog
* Amazon Athena
* AWS Lake Formation
* AWS S3 Lifecycle
