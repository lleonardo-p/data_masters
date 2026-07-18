# ADR-011: Qualidade de Dados e Quarentena

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP processa dados de múltiplas fontes com formatos, granularidades e níveis de confiabilidade diferentes.

Sem validações de qualidade, registros inválidos podem contaminar as camadas Silver, Gold e DW, prejudicando indicadores, dashboards e análises.

A arquitetura precisa definir regras para bloqueio, quarentena, alertas e rastreabilidade de problemas de dados.

## Decisão

Será adotada uma estratégia de qualidade de dados com três níveis de tratamento:

- **Bloqueante:** falhas críticas que impedem a continuidade do processamento.
- **Quarentena:** registros inválidos ou suspeitos que devem ser isolados para análise posterior.
- **Alerta:** desvios que não impedem o processamento, mas devem ser monitorados.

As validações deverão cobrir, quando aplicável:

- schema obrigatório;
- tipos de dados;
- campos nulos críticos;
- chaves de negócio;
- duplicidade;
- datas inválidas ou fora de intervalo;
- domínios e valores permitidos;
- volumetria;
- freshness;
- presença indevida de PII em camadas analíticas.

Registros em quarentena serão armazenados em área controlada do S3, separados por fonte, data de processamento e tipo de erro.

Padrão sugerido:

```text
s3://baip-data-lake/quarantine/<domain>/<source>/year=YYYY/month=MM/day=DD/error_type=<error_type>/
```

Os registros de quarentena devem conter metadados mínimos para rastreabilidade, como:

- `source_system`;
- `ingestion_date`;
- `processing_time`;
- `rule_name`;
- `error_code`;
- `error_message`;
- `raw_payload_reference` ou payload controlado;
- `pipeline_execution_id`.

## Justificativa

A separação entre bloqueio, quarentena e alerta evita tratar todos os problemas de dados da mesma forma.

Falhas críticas devem interromper o processamento para evitar propagação de dados inválidos. Registros pontuais com erro podem ser isolados em quarentena sem impedir o processamento de todo o lote. Desvios não críticos podem gerar alertas para investigação posterior.

A quarentena aumenta rastreabilidade e permite correção sem contaminar as camadas analíticas.

## Alternativas consideradas

- **Falhar o pipeline para qualquer erro:** aumenta segurança, mas reduz disponibilidade e pode bloquear cargas por problemas pontuais.
- **Ignorar registros inválidos:** simplifica o processamento, mas reduz confiabilidade e rastreabilidade.
- **Corrigir automaticamente todos os erros:** pode mascarar problemas de origem e gerar inconsistências.
- **Validar apenas na Gold:** detecta problemas tarde demais, após propagação para camadas intermediárias.

## Consequências

### Positivas

- Maior confiabilidade dos dados.
- Redução de contaminação em Silver, Gold e DW.
- Melhor rastreabilidade de erros.
- Possibilidade de reprocessamento de registros corrigidos.
- Separação clara entre erro crítico, erro pontual e alerta.

### Negativas / Trade-offs

- Aumenta complexidade dos pipelines.
- Exige manutenção de regras de qualidade.
- Pode gerar volume adicional de dados em quarentena.
- Regras muito rígidas podem bloquear dados úteis.
- Regras muito flexíveis podem permitir propagação de problemas.

## Escalabilidade e alternativas

Regras por registro devem ser combinadas com controles agregados: volumetria,
nulos, percentual de match, freshness e distribuição. Quarentena precisa de
lifecycle, métricas por código e procedimento de reprocessamento.

Glue Data Quality, Deequ ou Great Expectations serão avaliados quando volume e
reutilização de regras superarem a manutenção em código. Nem toda fonte precisa
da mesma implementação; severidade depende do impacto no consumidor.

## Critérios de evolução

Esta decisão deve ser revisada se:

- novos domínios exigirem regras específicas de qualidade;
- o volume de registros em quarentena crescer significativamente;
- houver necessidade de ferramenta dedicada de Data Quality;
- regras de negócio oficiais forem alteradas;
- dados reais forem processados;
- houver necessidade de workflow formal para correção e reprocessamento.

## Referências

- Data Quality Rules
- Great Expectations
- AWS Glue Data Quality
- Amazon S3
- Amazon CloudWatch
