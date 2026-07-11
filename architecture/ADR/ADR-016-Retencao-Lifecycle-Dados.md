# ADR-016: Retenção e Lifecycle de Dados

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP armazena dados em diferentes camadas com finalidades distintas: aterrissagem temporária, auditoria, tratamento, consumo analítico e indicadores near real-time.

Sem uma política clara de retenção e lifecycle, o custo de armazenamento tende a crescer, arquivos temporários podem se acumular e dados sensíveis podem permanecer armazenados além do necessário.

A estratégia de retenção deve considerar a finalidade de cada camada, a necessidade de reprocessamento, o custo de armazenamento, a rastreabilidade e os princípios de minimização de dados.

## Decisão

Será adotada uma estratégia de retenção por camada e tipo de dado.

As políticas iniciais serão:

- **Staging:** retenção curta de até **7 dias**, com exclusão automática após esse período.
- **Bronze:** retenção maior para auditoria, rastreabilidade e reprocessamento, com lifecycle para classes de armazenamento mais baratas quando aplicável.
- **Silver:** retenção alinhada à necessidade de reprocessamento, qualidade de dados e rastreabilidade dos dados tratados.
- **Gold/DW:** retenção conforme necessidade analítica, histórica e de consumo pelos indicadores.
- **Near real-time/DynamoDB:** uso de TTL para dados temporários quando aplicável.
- **Logs:** retenção limitada, sem registro de PII ou payloads sensíveis.

Os prazos exatos de retenção das camadas Bronze, Silver, Gold e DW serão definidos por domínio de dado. Para o MVP, apenas a Staging terá prazo fixo inicial de 7 dias.

Dados pessoais ou sensíveis devem seguir o princípio de minimização e não devem ser mantidos por mais tempo do que o necessário para a finalidade definida.

As políticas de lifecycle devem ser aplicadas principalmente no Amazon S3, considerando expurgo, transição de storage class e redução de custo ao longo do tempo.

## Justificativa

A camada Staging possui finalidade temporária e operacional. Ela serve apenas como área de aterrissagem e preparação inicial dos dados antes da persistência em camadas definitivas. Por isso, sua retenção deve ser curta para evitar acúmulo desnecessário de arquivos e reduzir custo.

As camadas Bronze, Silver e Gold possuem finalidades diferentes e, portanto, não devem seguir a mesma política de retenção. A Bronze precisa preservar maior capacidade de auditoria e reprocessamento. A Silver deve manter dados tratados enquanto forem úteis para rastreabilidade e reconstrução das camadas analíticas. A Gold/DW deve preservar o histórico necessário para análise e consumo.

A adoção de lifecycle reduz custo, melhora governança e evita retenção indefinida de dados sem finalidade clara.

## Alternativas consideradas

- **Retenção indefinida:** simples de implementar, mas aumenta custo, dificulta governança e eleva o risco de retenção indevida de dados.
- **Exclusão agressiva:** reduz custo, mas pode prejudicar auditoria, rastreabilidade e reprocessamento.
- **Retenção única para todas as camadas:** simplifica a configuração, mas ignora diferenças de finalidade, criticidade e sensibilidade entre Staging, Bronze, Silver, Gold, DW, logs e dados near real-time.
- **Lifecycle apenas manual:** reduz automação e aumenta risco de esquecimento, inconsistência e acúmulo de dados antigos.

## Consequências

### Positivas

- Redução de custo de armazenamento.
- Limpeza automática da camada Staging.
- Melhor aderência ao princípio de minimização de dados.
- Menor risco de retenção indevida.
- Governança mais clara por camada.
- Melhor controle sobre dados temporários, históricos e analíticos.
- Possibilidade de evolução para políticas de retenção mais específicas por domínio ou tipo de dado.

### Negativas / Trade-offs

- Exige configuração e manutenção de políticas de lifecycle.
- Pode dificultar reprocessamento se dados forem expirados cedo demais.
- Necessita documentação clara dos prazos de retenção.
- Regras incorretas de lifecycle podem excluir dados ainda necessários.
- Pode exigir revisão caso dados reais ou sensíveis sejam utilizados.

## Critérios de evolução

Esta decisão deve ser revisada se:

- dados reais forem processados;
- surgirem requisitos legais específicos de retenção;
- houver necessidade de retenção diferenciada por domínio de dado;
- o custo de armazenamento crescer acima do previsto;
- a frequência de reprocessamentos mudar;
- a janela de auditoria precisar ser ampliada;
- dados sensíveis passarem a ser armazenados em maior escala;
- houver necessidade de políticas formais de expurgo por solicitação do titular de dados.

## Referências

- Amazon S3 Lifecycle
- Amazon S3 Storage Classes
- DynamoDB TTL
- CloudWatch Logs Retention
- LGPD
