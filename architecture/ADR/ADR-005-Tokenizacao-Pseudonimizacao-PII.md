# ADR-005: Tokenização e Pseudonimização de Dados Pessoais

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui um fluxo de eventos hospitalares simulados que pode conter identificadores pessoais, como CPF ou identificadores equivalentes.

Embora o projeto esteja em fase de MVP e utilize dados simulados, a arquitetura deve demonstrar boas práticas de privacidade, minimização de dados, proteção de PII e redução do risco de exposição de dados pessoais.

Caso o projeto evolua para o uso de dados reais, identificadores como CPF deverão ser tratados como dados pessoais e os eventos hospitalares poderão envolver dados sensíveis relacionados à saúde. Portanto, a arquitetura deve ser desenhada desde o início com separação clara entre dados identificáveis e dados analíticos.

## Decisão

Será adotado um serviço lógico de identidade para gerar um identificador técnico, como `patient_id`, a partir de um identificador sensível, como CPF ou identificador equivalente.

A estratégia adotada será tratada como **tokenização/pseudonimização**, e não como anonimização irreversível.

O CPF ou identificador sensível não deverá ser propagado para as camadas analíticas do Data Lake, incluindo Silver, Gold, Data Warehouse, dashboards, relatórios, logs ou tabelas de consumo.

Quando necessário, o CPF poderá existir apenas em uma área restrita de ingestão ou em um repositório isolado de identidade, com acesso controlado, criptografia, auditoria e retenção limitada.

O identificador técnico `patient_id` deverá ser utilizado nas camadas Silver e Gold para permitir deduplicação, reconciliação e análise longitudinal sem expor diretamente o identificador sensível.

Regras principais:

- CPF ou identificador sensível não deve ser propagado para Silver, Gold, DW, dashboards, relatórios ou logs.
- O CPF deve ser removido, mascarado ou substituído por `patient_id` o mais cedo possível no pipeline.
- O mapeamento entre identificador sensível e `patient_id`, quando existir, deve ficar isolado, criptografado e com acesso restrito.
- O segredo usado para geração do token deve ser protegido por AWS KMS e/ou AWS Secrets Manager.
- O token deve ser determinístico quando necessário para deduplicação, reconciliação e análise longitudinal.
- O processo de geração do token deve normalizar o identificador de entrada antes da tokenização.
- Logs de aplicação, Glue Jobs, Lambda, Step Functions e CloudWatch não devem registrar CPF, payloads sensíveis ou dados identificáveis.
- O acesso ao repositório de identidade deve seguir o princípio do menor privilégio.
- A operação deve ser auditável por logs de acesso e trilhas de auditoria.
- Dados pessoais devem possuir política explícita de retenção e expurgo.
- Em caso de uso de dados reais, a base legal, a finalidade do tratamento e a necessidade de RIPD deverão ser avaliadas com apoio jurídico, DPO ou responsável de privacidade.

## Justificativa

A pseudonimização reduz o risco de exposição de dados pessoais ao substituir identificadores diretos por identificadores técnicos. Isso permite análises por paciente, deduplicação e acompanhamento longitudinal sem carregar CPF para as camadas analíticas.

A distinção entre pseudonimização e anonimização é essencial. Como pode existir segredo, regra de geração ou mapeamento capaz de associar o `patient_id` ao CPF original, o dado pseudonimizado ainda deve ser tratado como dado pessoal em contextos de risco de reidentificação.

Essa decisão melhora a aderência aos princípios de minimização, segurança, prevenção e privacidade desde a concepção. Para o MVP, a abordagem demonstra boas práticas mesmo com dados simulados. Para um cenário real, ela cria uma base técnica mais segura para evolução regulatória e operacional.

## Alternativas consideradas

- **Manter CPF nas camadas analíticas:** rejeitado por aumentar o risco de exposição, ampliar a superfície de acesso a PII e reduzir aderência a boas práticas de privacidade e minimização de dados.
- **Remover qualquer identificador do pipeline:** reduz o risco de exposição, mas inviabiliza deduplicação, reconciliação entre fontes e análise longitudinal de eventos por paciente.
- **Aplicar hash simples sem segredo:** rejeitado porque identificadores como CPF possuem formato previsível e podem estar sujeitos a ataques de dicionário ou força bruta.
- **Anonimização completa:** reduz o risco de reidentificação, mas pode inviabilizar análises longitudinais, deduplicação e reconciliação necessárias para o caso de uso.
- **Criptografar CPF e mantê-lo nas camadas analíticas:** protege o dado em repouso, mas ainda propaga o identificador sensível para áreas de maior consumo, aumentando o risco operacional e a complexidade de controle de acesso.

## Consequências

### Positivas

- Redução da exposição de PII.
- Menor propagação de CPF no Data Lake.
- Possibilidade de análise longitudinal sem revelar diretamente a identidade do paciente.
- Melhor aderência aos princípios de minimização e privacidade desde a concepção.
- Separação clara entre domínio de identidade e domínio analítico.
- Redução de risco em logs, dashboards, tabelas de consumo e consultas SQL.
- Base mais adequada para evolução futura com dados reais.

### Negativas / Trade-offs

- Maior complexidade no pipeline de ingestão.
- Necessidade de proteger chaves, segredos e regras de geração de token.
- Necessidade de controle rigoroso de acesso ao repositório de identidade.
- Token determinístico pode permitir correlação entre registros.
- O dado pseudonimizado ainda pode ser considerado dado pessoal se houver risco de reidentificação.
- Rotação de segredo exige estratégia de versionamento e possível reprocessamento de tokens.
- Uso de dados reais pode exigir avaliação jurídica, RIPD e controles adicionais de governança.

## Escalabilidade e alternativas

O serviço de identidade deve distribuir chaves e evitar hot partition. Chamadas
KMS ou Secrets Manager por evento podem virar gargalo; o segredo pode ser
reutilizado em memória pelo tempo permitido, sem ser registrado. Rotação exige
`hash_version` e estratégia de transição.

Multi-Region requer decidir se o identity store será regional ou replicado,
como evitar tokens divergentes e onde PII pode ser processada. Global Tables não
substitui análise de residência, consistência e conflito.

## Critérios de evolução

Esta decisão deve ser revisada se:

- dados reais forem utilizados;
- houver necessidade de reversibilidade controlada;
- novas fontes trouxerem identificadores diferentes de CPF;
- houver exigência de anonimização plena;
- houver necessidade de compartilhamento externo dos dados;
- a plataforma passar a tratar dados pessoais sensíveis em escala;
- houver mudança nos requisitos jurídicos, regulatórios ou de governança;
- houver necessidade de rotação periódica do segredo de tokenização;
- o risco de reidentificação aumentar devido ao cruzamento com novas bases.

## Referências

- LGPD
- ANPD — Estudos e orientações sobre anonimização e pseudonimização
- ANPD — Relatório de Impacto à Proteção de Dados Pessoais (RIPD)
- AWS KMS
- AWS Secrets Manager
- Privacy by Design
