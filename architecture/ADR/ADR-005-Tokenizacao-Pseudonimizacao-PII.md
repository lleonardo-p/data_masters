# ADR-005: Tokenização e Pseudonimização de Dados Pessoais

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui fluxo simulado de eventos hospitalares que pode conter identificadores pessoais, como CPF ou identificadores equivalentes.

Mesmo em um projeto simulado, a arquitetura deve demonstrar boas práticas de privacidade, minimização de dados e prevenção de exposição de PII.

## Decisão

Será adotado um serviço lógico de identidade para gerar um identificador técnico, como `patient_id`, a partir de um identificador sensível.

A estratégia será tratada como **tokenização/pseudonimização**, não como anonimização irreversível.

Regras principais:

- CPF ou identificador sensível não deve ser propagado para Silver, Gold, DW, dashboards ou logs.
- O mapeamento entre identificador sensível e `patient_id`, quando existir, deve ficar isolado e criptografado.
- O segredo usado para geração de token deve ser protegido por KMS/Secrets Manager.
- O token deve ser determinístico quando necessário para deduplicação e reconciliação.

## Justificativa

A pseudonimização reduz risco de exposição e permite análise longitudinal sem carregar PII para camadas analíticas.

A distinção entre pseudonimização e anonimização é importante: se houver possibilidade de reversão ou reidentificação, o dado ainda deve ser tratado com cuidado.

## Alternativas consideradas

- **Manter CPF nas camadas analíticas:** rejeitado por risco e baixa aderência à LGPD.
- **Remover qualquer identificador:** reduz risco, mas inviabiliza deduplicação e análise de recorrência.
- **Hash simples sem segredo:** insuficiente contra ataques de dicionário em identificadores previsíveis.

## Consequências

### Positivas

- Redução de exposição de PII.
- Possibilidade de análise por paciente sem revelar identidade.
- Melhor aderência a minimização de dados.
- Base mais profissional para LGPD.

### Negativas

- Maior complexidade no pipeline.
- Necessidade de proteger chaves e segredos.
- Token ainda pode ser dado pessoal se permitir reidentificação indireta.

## Critérios de evolução

Revisar esta decisão se:

- dados reais forem usados;
- houver necessidade de reversibilidade controlada;
- novas fontes trouxerem identificadores diferentes;
- requisitos jurídicos exigirem anonimização plena.

## Referências

- LGPD
- AWS KMS
- AWS Secrets Manager
- Privacy by Design
