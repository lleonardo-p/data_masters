# ADR-004: Segurança e Governança de Dados

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP manipula dados públicos e eventos hospitalares simulados que podem conter identificadores sensíveis em estágios iniciais do pipeline.

A arquitetura precisa evitar exposição de PII, controlar acesso por camada, registrar auditoria, proteger dados em repouso e em trânsito e manter aderência à LGPD.

## Decisão

A segurança será baseada em:

- **AWS IAM** com princípio do menor privilégio;
- segregação de permissões por camada: Bronze, Silver, Gold e DW;
- bloqueio de acesso público nos buckets S3;
- criptografia com **AWS KMS** quando aplicável;
- logs e auditoria com CloudWatch e CloudTrail;
- ausência de PII nas camadas Gold, DW, dashboards e APIs analíticas;
- evolução para **AWS Lake Formation** para governança fina de tabelas, colunas e permissões.

## Justificativa

IAM e políticas de bucket atendem ao MVP com baixa complexidade. Para produção, Lake Formation, KMS e auditoria centralizada tornam a governança mais robusta e adequada a dados sensíveis.

A proteção deve ocorrer desde a ingestão, evitando que dados pessoais sejam propagados para camadas analíticas.

## Alternativas consideradas

- **Acesso amplo entre serviços:** rejeitado por risco elevado e baixa aderência à LGPD.
- **Segurança apenas no bucket S3:** insuficiente para governança por tabela, coluna e consumidor.
- **Ferramentas externas como Collibra/DataHub:** úteis para governança corporativa, mas aumentam escopo e operação no MVP.

## Consequências

### Positivas

- Redução do risco de vazamento.
- Melhor rastreabilidade e auditoria.
- Separação clara entre dados brutos, tratados e analíticos.
- Evolução possível para governança granular.

### Negativas

- Maior complexidade na configuração de permissões.
- Necessidade de revisão contínua de políticas IAM.
- Risco de má configuração se não houver automação e validação.

## Critérios de evolução

Revisar esta decisão se:

- novos consumidores exigirem acesso granular por coluna ou linha;
- dados reais substituírem dados simulados;
- houver exigência formal de auditoria e trilha regulatória;
- o número de domínios, tabelas e consumidores crescer significativamente.

## Referências

- AWS IAM Best Practices
- AWS Lake Formation
- AWS KMS
- AWS CloudTrail
- LGPD
