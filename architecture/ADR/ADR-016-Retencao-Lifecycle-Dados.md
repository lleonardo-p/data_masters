# ADR-016: Retenção e Lifecycle de Dados

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP armazena dados em diferentes camadas com finalidades distintas: auditoria, tratamento, consumo analítico e indicadores near real-time.

Sem política de retenção, o custo tende a crescer e dados sensíveis podem permanecer armazenados além do necessário.

## Decisão

Será adotada uma estratégia de retenção por camada e tipo de dado:

- **Bronze:** retenção maior para auditoria e reprocessamento, com lifecycle para storage class mais barata.
- **Silver:** retenção alinhada à necessidade de reprocessamento e rastreabilidade.
- **Gold/DW:** retenção conforme necessidade analítica e histórica.
- **Near real-time/DynamoDB:** TTL para dados temporários quando aplicável.
- **Logs:** retenção limitada e sem PII.

Dados sensíveis devem seguir princípio de minimização e não devem ser mantidos sem necessidade.

## Justificativa

Lifecycle reduz custo e melhora governança. A retenção diferenciada evita tratar todos os dados da mesma forma, respeitando finalidade, uso e sensibilidade.

## Alternativas consideradas

- **Retenção indefinida:** simples, mas aumenta custo e risco.
- **Exclusão agressiva:** reduz custo, mas prejudica auditoria e reprocessamento.
- **Retenção única para todas as camadas:** ignora diferenças de finalidade e sensibilidade.

## Consequências

### Positivas

- Redução de custo de armazenamento.
- Melhor aderência à minimização de dados.
- Menor risco de retenção indevida.
- Governança mais clara por camada.

### Negativas

- Exige configuração e revisão de lifecycle.
- Pode dificultar reprocessamento se dados forem expirados cedo demais.
- Necessita documentação clara de prazos.

## Critérios de evolução

Revisar esta decisão se:

- surgirem requisitos legais específicos de retenção;
- dados reais forem processados;
- o custo de armazenamento crescer acima do previsto;
- a frequência de reprocessamentos mudar.

## Referências

- Amazon S3 Lifecycle
- DynamoDB TTL
- CloudWatch Logs Retention
- LGPD
