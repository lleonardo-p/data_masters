# ADR-020: Estratégia de Ambientes e Contas AWS

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa separar desenvolvimento, testes e produção para reduzir risco de mudanças, controlar custos e proteger dados.

Em um MVP, uma única conta pode ser suficiente. Em produção, a separação por contas e ambientes melhora governança, segurança e rastreabilidade.

## Decisão

Para o MVP, poderá ser usada uma única conta AWS com separação lógica por ambiente, tags, prefixos e variáveis Terraform.

Para produção, a arquitetura deverá evoluir para contas separadas, no mínimo:

- **dev:** desenvolvimento e experimentação;
- **staging:** validação integrada;
- **prod:** ambiente produtivo;
- opcionalmente **security/logging:** auditoria centralizada.

## Justificativa

Separar ambientes reduz o risco de alterações acidentais em produção e facilita controle de acesso e custo.

A decisão preserva simplicidade no MVP, mas define um caminho profissional de evolução.

## Alternativas consideradas

- **Uma conta única para tudo:** simples, mas aumenta risco operacional e dificulta governança.
- **Contas separadas desde o início:** mais profissional, mas pode ser excessivo para o MVP.
- **Ambientes apenas por branch Git:** insuficiente, pois não isola recursos cloud.

## Consequências

### Positivas

- Melhor isolamento entre ambientes.
- Controle de custo por ambiente.
- Menor risco de impacto em produção.
- Aderência a práticas corporativas.

### Negativas

- Mais contas e permissões para gerenciar.
- Maior complexidade no Terraform e CI/CD.
- Necessidade de padronização de tags e naming.

## Critérios de evolução

Adotar contas separadas quando:

- houver dados reais;
- mais pessoas contribuírem no projeto;
- houver CI/CD formal;
- a arquitetura for apresentada como produção corporativa.

## Referências

- AWS Organizations
- AWS Control Tower
- AWS Multi-Account Strategy
