# ADR-008: Store Near Real-Time com Amazon DynamoDB

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O fluxo near real-time precisa disponibilizar indicadores recentes de triagem e suspeita de arboviroses com baixa latência.

Esses dados têm perfil operacional/agregado, diferente do histórico analítico armazenado no Data Lake.

## Decisão

Será utilizado **Amazon DynamoDB** como store near real-time para indicadores agregados.

A modelagem deverá priorizar padrões de acesso, como:

- indicadores por UF, município, doença e janela temporal;
- últimas atualizações por fonte;
- controle de eventos processados para idempotência;
- TTL para dados temporários, quando aplicável.

A tabela não deve armazenar PII.

## Justificativa

DynamoDB oferece baixa latência, operação gerenciada e escalabilidade automática para leituras e escritas orientadas a chave.

Ele é adequado para indicadores recentes e operacionais, enquanto o S3/Gold/DW permanece como fonte oficial para análises consolidadas.

## Alternativas consideradas

- **Amazon RDS/PostgreSQL:** bom para SQL relacional, mas exige mais operação e escalabilidade planejada.
- **Amazon ElastiCache/Redis:** excelente para cache, mas menos adequado como store persistente principal.
- **Amazon OpenSearch:** bom para busca e exploração textual, mas desnecessário para agregados simples.
- **S3/Athena diretamente:** melhor para histórico analítico, mas não para baixa latência operacional.

## Consequências

### Positivas

- Baixa latência.
- Baixo esforço operacional.
- Escalabilidade gerenciada.
- Boa integração com Lambda.

### Negativas

- Modelagem depende dos padrões de consulta.
- Consultas ad hoc são limitadas.
- Risco de hot partition se a chave for mal definida.

## Critérios de evolução

Revisar esta decisão se:

- forem necessárias consultas relacionais complexas;
- o padrão de acesso ficar imprevisível;
- houver hot partitions recorrentes;
- o dado near real-time precisar ser consultado de forma analítica ampla.

## Referências

- Amazon DynamoDB
- DynamoDB single-table design
- DynamoDB TTL
