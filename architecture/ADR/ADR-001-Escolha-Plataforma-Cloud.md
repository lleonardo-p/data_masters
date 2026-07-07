# ADR-001: Escolha da Plataforma Cloud

* **Status:** Aceito
* **Data:** 2026-07-07
* **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP (Brazil Arbovirus Intelligence Platform) precisa de uma plataforma cloud para suportar ingestões batch, processamento de dados, armazenamento em Data Lake, consultas analíticas, componentes near real-time e observabilidade.

A solução deve equilibrar baixo custo, simplicidade operacional, escalabilidade, segurança, aderência à LGPD e possibilidade de evolução futura para um ambiente produtivo mais resiliente.

Como o projeto está em fase de MVP, a arquitetura deve priorizar velocidade de implementação, redução de complexidade operacional e uso de tecnologias já conhecidas.

## Decisão

A arquitetura será implementada na **Amazon Web Services (AWS)**.

Para o MVP, a solução será implantada em **uma única região AWS**, sem estratégia explícita de **Multi-AZ**, **Multi-Region** ou **Multicloud**.

A arquitetura utilizará serviços gerenciados da AWS sempre que possível, aproveitando a disponibilidade nativa desses serviços quando aplicável, mas sem desenhar uma camada adicional de alta disponibilidade entre zonas ou regiões neste momento.

## Justificativa

A escolha da AWS foi feita para acelerar o desenvolvimento do MVP, reduzir curva de aprendizado e aproveitar familiaridade prévia com os principais serviços utilizados na arquitetura.

A AWS oferece serviços gerenciados maduros para Engenharia de Dados, como Amazon S3, AWS Glue, Amazon Athena, AWS Lambda, Amazon SQS, Amazon DynamoDB, AWS Step Functions e Amazon CloudWatch.

O uso de uma única cloud reduz o tempo necessário para estudo, capacitação, integração entre serviços e implantação inicial. Isso permite concentrar o esforço do projeto na modelagem da arquitetura de dados, nos fluxos de ingestão, no processamento batch, na governança e na entrega dos indicadores analíticos.

Não há, no escopo atual, requisito formal de alta disponibilidade Multi-AZ, operação Multi-Region ou estratégia Multicloud. Caso o projeto evolua para um cenário de alta demanda, maior criticidade, requisitos agressivos de RTO/RPO ou necessidade de maior resiliência, a arquitetura poderá ser revisada para incluir Multi-AZ, Multi-Region ou até Multicloud.

## Alternativas consideradas

* **Microsoft Azure:** possui boa integração com ferramentas corporativas e Power BI, porém aumentaria a curva de aprendizado e o tempo de implementação do MVP. Como o objetivo atual é acelerar a entrega com ferramentas já conhecidas, Azure não foi priorizado.
* **Google Cloud Platform:** oferece uma stack analítica forte, especialmente com BigQuery e serviços gerenciados de dados. No entanto, exigiria maior tempo de estudo e capacitação para este projeto, reduzindo a velocidade de implementação do MVP em comparação com a AWS.
* **On-premises:** oferece maior controle sobre a infraestrutura, mas aumentaria significativamente o esforço operacional, o tempo de implantação e a complexidade de escalabilidade.
* **Multicloud:** poderia reduzir dependência de fornecedor em cenários mais maduros, mas adicionaria complexidade de rede, segurança, governança, observabilidade, custos e operação sem benefício proporcional para o MVP.

## Consequências

### Positivas

* Redução do tempo de desenvolvimento.
* Menor curva de aprendizado.
* Uso de serviços gerenciados e integrados.
* Menor esforço operacional no MVP.
* Boa aderência a cenários de Data Lake, processamento batch, consultas analíticas e observabilidade.
* Possibilidade de evolução gradual para maior resiliência e escalabilidade.

### Negativas / Trade-offs

* Dependência inicial do ecossistema AWS.
* Menor portabilidade para outros provedores cloud.
* Ausência de estratégia explícita de Multi-AZ e Multi-Region no MVP.
* Necessidade de revisão arquitetural caso a solução evolua para um ambiente produtivo crítico.

## Critérios de evolução

Esta decisão deve ser revisada se:

* houver exigência formal de Multicloud;
* houver necessidade de operação Multi-Region;
* houver requisitos mais agressivos de RTO/RPO;
* houver necessidade de baixa latência em diferentes regiões geográficas;
* houver requisito regulatório de residência de dados fora da região escolhida;
* o volume de dados ou a criticidade do processamento exigir maior resiliência;
* o projeto evoluir de MVP para uma plataforma produtiva de missão crítica.

## Referências

* AWS Well-Architected Framework
* AWS Architecture Center
* AWS Free Tier
