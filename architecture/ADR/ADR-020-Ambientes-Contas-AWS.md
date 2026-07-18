# ADR-020: Ambientes e Contas AWS

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa separar recursos, configurações e dados por ambiente para evitar mistura entre desenvolvimento, testes e eventual produção.

No MVP, o custo e a simplicidade são fatores importantes. Em uma evolução produtiva, isolamento mais forte entre ambientes pode ser necessário.

## Decisão

No MVP, a arquitetura poderá utilizar **uma única conta AWS** com separação lógica por ambiente.

A separação lógica deverá ser feita por:

- prefixos de recursos;
- tags padronizadas;
- variáveis Terraform;
- buckets, paths ou databases separados quando aplicável;
- permissões IAM específicas por finalidade.

A separação lógica por prefixos, tags e variáveis Terraform atende ao MVP, mas não oferece o mesmo nível de isolamento de contas separadas.

Para evolução produtiva, deverá ser considerada uma estratégia multi-account, com contas separadas para ambientes como:

- desenvolvimento;
- staging/homologação;
- produção;
- segurança/logging, quando necessário.

## Justificativa

Uma única conta reduz custo, complexidade e tempo de configuração no MVP.

A separação lógica permite organizar recursos e evitar conflitos básicos entre ambientes, mantendo simplicidade operacional.

Para produção, contas separadas oferecem melhor isolamento, controle de acesso, blast radius reduzido e governança mais forte.

## Alternativas consideradas

- **Multi-account desde o início:** oferece maior isolamento, mas aumenta complexidade, configuração e custo para o MVP.
- **Sem separação de ambientes:** simplifica o início, mas aumenta risco de sobrescrita, confusão de dados e erros operacionais.
- **Ambientes apenas por branch de código:** insuficiente para isolar recursos cloud, permissões e dados.
- **Conta única sem tags ou prefixos:** reduz esforço inicial, mas dificulta governança e rastreabilidade.

## Consequências

### Positivas

- Menor custo e complexidade no MVP.
- Organização mínima por ambiente.
- Facilidade para criar e destruir recursos de teste.
- Possibilidade de evolução para multi-account.
- Melhor rastreabilidade por tags e prefixos.

### Negativas / Trade-offs

- Menor isolamento entre ambientes.
- Maior risco de impacto cruzado em caso de erro de configuração.
- IAM precisa ser cuidadosamente definido para evitar permissões amplas.
- Não substitui uma estratégia multi-account produtiva.

## Escalabilidade e alternativas

Mais equipes e dados reais exigem contas separadas por ambiente e, conforme
risco, contas de segurança/log archive. AWS Organizations e SCPs reduzem blast
radius; roles cross-account substituem credenciais persistentes.

Compartilhamento de dados pode usar Lake Formation cross-account em vez de
copiar todos os datasets. Custos, quotas e observabilidade devem receber tags e
budgets por conta/produto.

## Critérios de evolução

Esta decisão deve ser revisada se:

- o projeto evoluir para produção;
- múltiplos usuários ou times passarem a operar a plataforma;
- dados reais forem processados;
- houver exigência de isolamento formal entre ambientes;
- houver necessidade de conta dedicada para logs, segurança ou auditoria;
- recursos críticos exigirem redução de blast radius.

## Referências

- AWS Organizations
- AWS Account Management
- AWS IAM
- Terraform Workspaces
- AWS Tagging Best Practices
