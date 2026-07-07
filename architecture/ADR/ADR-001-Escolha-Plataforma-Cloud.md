# ADR-001: Escolha da Plataforma Cloud

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP (Brazil Arbovirus Intelligence Platform) precisa de uma base cloud para executar ingestões batch, processamento distribuído, armazenamento em Data Lake, consultas analíticas, componentes near real-time e observabilidade.

A plataforma deve equilibrar baixo custo, simplicidade operacional, escalabilidade, segurança, aderência à LGPD e possibilidade de evolução para um ambiente produtivo com maior disponibilidade.

## Decisão

A arquitetura será implementada na **Amazon Web Services (AWS)**.

Para o MVP, a solução será implantada em **uma única região AWS**, utilizando serviços gerenciados e recursos **Multi-AZ quando suportados nativamente** pelo serviço.

Não será adotada arquitetura multicloud neste momento.

## Justificativa

A AWS oferece serviços gerenciados maduros para Engenharia de Dados, como Amazon S3, AWS Glue, Amazon Athena, AWS Lambda, Amazon SQS, Amazon DynamoDB, AWS Step Functions e Amazon CloudWatch.

Essa escolha reduz esforço operacional, acelera a implementação e permite evolução gradual para requisitos mais robustos de segurança, governança, resiliência e escalabilidade.

## Alternativas consideradas

- **Microsoft Azure:** forte integração com Power BI e ambiente corporativo, mas aumentaria a curva de aprendizado e o tempo de implementação para este projeto.
- **Google Cloud Platform:** excelente stack analítica, especialmente com BigQuery, mas exigiria adaptação da arquitetura proposta.
- **On-premises:** maior controle da infraestrutura, porém com alto esforço operacional, menor elasticidade e maior tempo de implantação.
- **Multicloud:** aumenta complexidade, custo e operação sem benefício proporcional para o escopo atual.

## Consequências

### Positivas

- Menor tempo de desenvolvimento.
- Uso de serviços gerenciados.
- Boa integração entre serviços de dados e analytics.
- Escalabilidade com baixo esforço operacional.
- Base adequada para evolução profissional da arquitetura.

### Negativas

- Dependência do ecossistema AWS.
- Menor portabilidade para outros provedores.
- Necessidade de adaptação caso a solução evolua para multicloud.

## Critérios de evolução

Esta decisão deve ser revisada se:

- houver exigência formal de multicloud;
- houver necessidade de baixa latência em múltiplas regiões;
- houver requisito regulatório de residência de dados fora da região escolhida;
- o ambiente evoluir de MVP para produção crítica com RTO/RPO mais agressivos.

## Referências

- AWS Well-Architected Framework
- AWS Free Tier
- AWS Architecture Center
