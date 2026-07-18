# ADR-017: Infraestrutura como Código com Terraform

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP depende de múltiplos recursos AWS, como buckets S3, filas SQS, funções Lambda, tabelas DynamoDB, jobs Glue, Step Functions, permissões IAM, alarmes e configurações de observabilidade.

Criar e manter esses recursos manualmente aumenta risco de inconsistência, dificulta reprodutibilidade e reduz controle sobre mudanças.

## Decisão

A infraestrutura será definida como código utilizando **Terraform**.

O Terraform deverá ser utilizado para provisionar e versionar os principais recursos da arquitetura.

As configurações devem seguir boas práticas como:

- módulos reutilizáveis quando fizer sentido;
- variáveis por ambiente;
- tags padronizadas;
- separação entre código de infraestrutura e código de aplicação;
- validação em pull request;
- análise estática quando aplicável;
- uso de `prevent_destroy` para recursos críticos quando necessário.

No MVP, o estado poderá ser local durante experimentação controlada. Para ambientes compartilhados ou produtivos, o backend remoto com locking será obrigatório.

## Justificativa

Terraform permite versionar a infraestrutura, revisar mudanças, reproduzir ambientes e reduzir configuração manual.

A escolha também aproxima o projeto de práticas profissionais de Cloud Engineering, Data Platform e DevOps.

Permitir estado local apenas em experimentação evita complexidade inicial desnecessária. Exigir backend remoto em ambientes compartilhados ou produtivos reduz risco de concorrência, perda de estado e alterações não rastreadas.

## Alternativas consideradas

- **Provisionamento manual no console AWS:** rápido para testes, mas pouco reprodutível e sujeito a erros.
- **AWS CloudFormation:** nativo da AWS, mas menos portátil e com menor familiaridade para este projeto.
- **AWS CDK:** poderoso e flexível, mas adiciona dependência de linguagem e abstrações adicionais.
- **Scripts CLI:** úteis para automação simples, mas menos adequados para controle declarativo de estado.

## Consequências

### Positivas

- Infraestrutura versionada e reprodutível.
- Redução de configuração manual.
- Melhor controle de mudanças.
- Facilidade para recriar ambientes.
- Base para evolução com CI/CD de infraestrutura.
- Melhor rastreabilidade de recursos cloud.

### Negativas / Trade-offs

- Exige organização do código Terraform.
- Requer cuidado com estado e locking.
- Mudanças incorretas podem afetar recursos críticos.
- Pode aumentar esforço inicial em comparação com criação manual.

## Escalabilidade e alternativas

Com mais ambientes, o estado deve usar backend remoto com locking, criptografia
e acesso separado. Módulos precisam de versões e testes; um módulo genérico
demais pode aumentar blast radius. Planos binários, state e secrets não devem
ser versionados.

Multi-account e Multi-Region exigem providers/roles explícitos e pipelines com
aprovação. Atlantis, Terraform Cloud ou CI corporativo serão avaliados quando
concorrência de mudanças e segregação de funções justificarem um control plane.

## Critérios de evolução

Esta decisão deve ser revisada se:

- o projeto adotar outra ferramenta corporativa de IaC;
- múltiplos times passarem a manter a infraestrutura;
- houver necessidade de módulos mais avançados ou registry privado;
- o ambiente evoluir para múltiplas contas AWS;
- forem exigidos pipelines formais de aprovação e deploy de infraestrutura.

## Referências

- Terraform
- Terraform AWS Provider
- AWS IAM
- Terraform Remote State
- Infrastructure as Code
