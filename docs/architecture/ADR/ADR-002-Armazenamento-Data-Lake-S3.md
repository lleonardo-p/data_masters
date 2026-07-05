# ADR-002: Armazenamento do Data Lake no Amazon S3

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa armazenar dados de múltiplas fontes, incluindo saúde pública, clima, eventos ambientais, infraestrutura de saúde e eventos hospitalares simulados.

A solução deve suportar dados brutos, tratados e analíticos, com baixo custo, reprocessamento, auditoria, particionamento, integração com catálogo e consulta SQL.

## Decisão

O **Amazon S3** será a camada principal de armazenamento do Data Lake.

Os dados serão organizados em arquitetura **Medallion**:

- **Bronze:** dados brutos, preservados no formato original ou semi-original.
- **Silver:** dados tratados, padronizados, deduplicados, enriquecidos e pseudonimizados quando necessário.
- **Gold:** dados analíticos, agregações, fatos, dimensões e indicadores para consumo.

O Data Lake deverá usar criptografia, bloqueio de acesso público, versionamento quando aplicável e políticas de lifecycle.

## Justificativa

O S3 é adequado para armazenamento escalável, durável e de baixo custo. Ele integra nativamente com AWS Glue, Glue Data Catalog, Athena, Lake Formation e outros serviços analíticos.

A separação Medallion permite rastreabilidade, reprocessamento, controle de qualidade e consumo analítico mais organizado.

## Alternativas consideradas

- **Amazon Redshift:** adequado para Data Warehouse, mas menos flexível como armazenamento bruto principal.
- **Amazon RDS/PostgreSQL:** bom para dados transacionais, mas limitado para Data Lake e grandes volumes analíticos.
- **Amazon DynamoDB:** adequado para baixa latência e indicadores near real-time, mas não para histórico analítico completo.
- **Armazenamento local/on-premises:** maior esforço operacional e menor elasticidade.

## Consequências

### Positivas

- Baixo custo de armazenamento.
- Escalabilidade e durabilidade.
- Suporte a reprocessamento e auditoria.
- Integração com ferramentas analíticas.
- Base adequada para Lakehouse.

### Negativas

- Exige governança forte de pastas, arquivos e particionamento.
- Pode gerar problema de pequenos arquivos se mal projetado.
- Depende de catálogo para consultas estruturadas.

## Critérios de evolução

Revisar esta decisão se:

- as tabelas Silver/Gold exigirem updates, deletes e time travel frequentes;
- houver necessidade de transações ACID no Data Lake;
- o volume de dados exigir otimização avançada de layout;
- consultas analíticas exigirem performance previsível de Data Warehouse dedicado.

## Referências

- Amazon S3
- AWS Glue Data Catalog
- Amazon Athena
- AWS Lake Formation
