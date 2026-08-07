# ADR-017: Infraestrutura como Código com Terraform

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

A BAIP utiliza diferentes serviços AWS nos fluxos Batch e NRT. A infraestrutura precisa ser reproduzível, versionada e consistente, evitando configurações manuais difíceis de auditar.

## Decisão

Utilizar Terraform para provisionar e gerenciar a infraestrutura AWS da plataforma.

O código contempla:

* armazenamento e catálogo de dados;
* processamento Batch e NRT;
* filas e DLQ;
* funções Lambda;
* orquestração;
* tabelas DynamoDB;
* API Gateway;
* KMS e Secrets Manager;
* funções e políticas IAM;
* logs, métricas, alarmes e notificações.

Os recursos são organizados por ambiente e módulos reutilizáveis. As alterações são verificadas com `terraform fmt`, `terraform validate` e `terraform plan` antes do `terraform apply`.

O plano e a aplicação são executados manualmente no MVP. Os componentes locais da pasta `api-local/` permanecem gerenciados pelo Docker Compose.

## Justificativa

O Terraform oferece:

* infraestrutura declarativa e versionada;
* visualização das alterações antes da aplicação;
* gerenciamento das dependências entre recursos;
* redução de configurações manuais;
* reprodução do ambiente;
* rastreabilidade das mudanças;
* possibilidade de reutilizar módulos em novos ambientes.

O Terraform também é uma tecnologia conhecida pelo desenvolvedor e atende aos serviços AWS utilizados no projeto.

## Limitação atual

O projeto não possui pipeline CI/CD para executar automaticamente validações, planos e aplicações.

Em uma evolução, o Terraform deverá ser integrado a um pipeline com:

* validação automática em pull requests;
* armazenamento do plano como artefato;
* análise de segurança do código;
* aprovação antes da aplicação;
* credenciais temporárias por federação;
* aplicação separada por ambiente;
* bloqueio de alterações diretas no ambiente produtivo.

## Alternativas

* **Provisionamento manual pelo console AWS:** não adotado porque dificultaria reprodução, auditoria e controle de mudanças.
* **AWS CloudFormation:** tecnicamente viável, mas não adotado devido à preferência e maior experiência do desenvolvedor com Terraform.
* **AWS CDK:** não adotado porque adicionaria geração de CloudFormation e maior dependência de código para definir a infraestrutura.
* **Pulumi:** não adotado devido à menor experiência do desenvolvedor e à ausência de benefício relevante para o projeto.
* **Scripts AWS CLI:** não adotados como mecanismo principal porque não oferecem o mesmo controle declarativo de estado e dependências.
