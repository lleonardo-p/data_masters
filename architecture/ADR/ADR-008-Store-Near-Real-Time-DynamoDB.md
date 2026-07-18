# ADR-008: Store Near Real-Time com Amazon DynamoDB

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa manter indicadores recentes em near real-time para consumo operacional, sem aguardar a consolidação batch diária.

Esses indicadores não substituem a camada oficial analítica do Data Lake, mas permitem uma visão atualizada de eventos recentes.

A store precisa ter baixa latência, escalabilidade, integração com Lambda e suporte a controle de idempotência.

## Decisão

O **Amazon DynamoDB** será utilizado como store operacional para dados e indicadores near real-time.

O DynamoDB poderá armazenar:

- indicadores recentes agregados;
- estado de processamento por `event_id`;
- controles de idempotência;
- dados temporários com TTL quando aplicável.

A modelagem das chaves deverá evitar concentração de escrita e leitura em uma única partição lógica. As chaves devem distribuir acesso por atributos como período, região, doença, tipo de evento ou identificador técnico, conforme o padrão de consulta.

A visão oficial consolidada continuará sendo produzida pelo fluxo batch em S3, Gold e DW.

## Justificativa

DynamoDB é adequado para acesso de baixa latência, alta disponibilidade gerenciada e integração nativa com Lambda.

A separação entre DynamoDB e Data Lake evita misturar visão operacional recente com histórico analítico oficial. Isso reduz o risco de duplicidade, facilita reconciliação e mantém o S3 como base consolidada para auditoria e análise histórica.

O uso de `event_id` e operações condicionais, como `condition_expression`, permite implementar idempotência e evitar dupla contagem em eventos reprocessados.

## Alternativas consideradas

- **Amazon RDS/PostgreSQL:** oferece SQL e consistência relacional, mas exige mais administração e pode ser menos eficiente para alto volume de eventos simples com baixa latência.
- **Amazon ElastiCache/Redis:** oferece latência muito baixa, mas não é ideal como store persistente principal de indicadores e controles de idempotência.
- **Athena direto no S3 para NRT:** simples para consulta analítica, mas inadequado para atualizações frequentes de baixa latência.
- **Manter indicadores apenas no batch:** simplifica arquitetura, mas não atende ao requisito near real-time.

## Consequências

### Positivas

- Baixa latência para leitura e escrita.
- Integração nativa com Lambda.
- Suporte a TTL para dados temporários.
- Boa opção para controle de idempotência.
- Redução de carga no Data Lake para consultas operacionais recentes.
- Separação entre visão recente e visão oficial consolidada.

### Negativas / Trade-offs

- Exige modelagem cuidadosa de chaves.
- Consultas analíticas complexas não são o ponto forte do DynamoDB.
- Risco de hot partition se a chave for mal definida.
- Necessidade de reconciliação com o batch oficial.
- Pode gerar custo se houver alto volume de escrita ou leitura sem modelagem adequada.

## Escalabilidade e alternativas

On-demand e adaptive capacity absorvem variação, mas não corrigem uma chave que
concentra todo o tráfego. O modelo deve distribuir writes por período,
localidade ou shard. Throttling, consumed capacity, latência e tamanho de item
validam a escala.

Global Tables é alternativa para serving Multi-Region após definir roteamento e
consistência. OpenSearch atende exploração; Redis atende cache. Nenhum substitui
automaticamente o store de idempotência.

## Critérios de evolução

Esta decisão deve ser revisada se:

- o volume de eventos near real-time crescer significativamente;
- as consultas exigirem filtros analíticos complexos;
- houver necessidade de joins ou agregações pesadas diretamente na store NRT;
- o custo de leitura/escrita no DynamoDB crescer acima do previsto;
- a arquitetura evoluir para streaming analítico com Kinesis, Kafka ou Flink.

## Referências

- Amazon DynamoDB
- DynamoDB TTL
- DynamoDB Conditional Writes
- AWS Lambda
- Amazon SQS
