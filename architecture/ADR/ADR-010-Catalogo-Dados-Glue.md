# ADR-010: Catálogo de Dados com AWS Glue Data Catalog

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa disponibilizar metadados técnicos das tabelas do Data Lake para processamento, consulta SQL e consumo analítico.

As camadas Silver, Gold e DW precisam ser consultáveis por Athena e integradas aos pipelines de processamento.

## Decisão

O **AWS Glue Data Catalog** será utilizado como catálogo técnico de metadados do Data Lake.

O catálogo deverá registrar bancos, tabelas, schemas, partições e localização dos datasets no S3.

As camadas **Bronze**, **Silver**, **Gold** e **DW** poderão ser catalogadas conforme necessidade de processamento, rastreabilidade e consulta.

A camada **Staging** não será catalogada por padrão, por possuir finalidade temporária. Quando necessário, poderá ter metadados técnicos mínimos para controle operacional, sem ser tratada como camada analítica.

## Justificativa

O Glue Data Catalog é integrado nativamente ao AWS Glue, Amazon Athena, Lake Formation e Amazon S3, reduzindo esforço operacional para descoberta e consulta de dados.

A centralização dos metadados facilita a execução dos jobs, o consumo via SQL e a organização das tabelas por camada e domínio.

Evitar catalogar a Staging por padrão reduz ruído no catálogo e reforça que essa área é temporária, não uma fonte oficial de consumo.

## Alternativas consideradas

- **Catálogo manual em documentação:** simples no início, mas não permite integração técnica com Athena e Glue.
- **DataHub:** oferece governança e linhagem mais avançadas, mas adiciona complexidade ao MVP.
- **Apache Atlas:** forte para governança, mas mais complexo de operar e fora do escopo inicial.
- **Sem catálogo:** simplifica a implantação inicial, mas dificulta consultas SQL, descoberta de dados e manutenção de partições.

## Consequências

### Positivas

- Integração nativa com Glue e Athena.
- Melhor organização de schemas e partições.
- Facilita descoberta técnica dos dados.
- Permite consulta SQL sobre dados no S3.
- Base para evolução futura com Lake Formation e governança mais avançada.

### Negativas / Trade-offs

- Exige manutenção de schemas e partições.
- Mudanças de schema precisam ser controladas.
- Catálogo técnico não substitui catálogo de negócio.
- Pode haver inconsistência se o layout no S3 e o catálogo não forem atualizados corretamente.

## Critérios de evolução

Esta decisão deve ser revisada se:

- houver necessidade de catálogo de negócio com glossário, ownership e linhagem;
- múltiplos times passarem a consumir a plataforma;
- houver exigência formal de governança de dados;
- o volume de tabelas crescer significativamente;
- a arquitetura adotar Lake Formation, DataHub ou outro catálogo corporativo.

## Referências

- AWS Glue Data Catalog
- Amazon Athena
- AWS Glue Crawlers
- AWS Lake Formation
