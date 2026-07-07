# ADR-010: Catálogo de Dados com AWS Glue Data Catalog

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa registrar metadados das tabelas do Data Lake e permitir consultas estruturadas via Athena, Glue e ferramentas analíticas.

Também é necessário manter rastreabilidade mínima sobre fonte, camada, owner, sensibilidade e atualização dos dados.

## Decisão

Será utilizado **AWS Glue Data Catalog** como catálogo técnico principal do Data Lake.

Cada tabela deverá conter metadados mínimos:

- camada: Bronze, Silver, Gold ou DW;
- domínio/fonte;
- owner técnico;
- classificação de sensibilidade;
- frequência de atualização;
- descrição do grão;
- localização no S3;
- formato e particionamento.

## Justificativa

O Glue Data Catalog possui integração nativa com Glue, Athena, Lake Formation e S3, reduzindo complexidade operacional.

Ele atende ao MVP e pode ser complementado por ferramentas de governança mais avançadas conforme a maturidade aumentar.

## Alternativas consideradas

- **Hive Metastore autogerenciado:** maior operação e menor aderência ao ecossistema serverless AWS.
- **DataHub/OpenMetadata:** ótimas ferramentas de catálogo corporativo, mas adicionam infraestrutura e escopo.
- **Catálogo manual em documentação:** simples, mas frágil e desatualizado com facilidade.

## Consequências

### Positivas

- Integração nativa com Athena e Glue.
- Catálogo centralizado para tabelas do Data Lake.
- Base para governança com Lake Formation.
- Menor esforço operacional.

### Negativas

- Metadados de negócio e lineage são limitados sem ferramentas adicionais.
- Requer disciplina para manter descrições e classificações.
- Crawlers mal configurados podem gerar schemas incorretos.

## Critérios de evolução

Revisar esta decisão se:

- houver necessidade forte de lineage ponta a ponta;
- múltiplos times consumirem e produzirem dados;
- o volume de datasets exigir portal de descoberta;
- metadados de negócio ficarem mais importantes que metadados técnicos.

## Referências

- AWS Glue Data Catalog
- Amazon Athena
- AWS Lake Formation
