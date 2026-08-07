# ADR-004: Segurança e Controle de Acesso

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

A BAIP processa dados públicos no fluxo Batch e dados pessoais sintéticos no fluxo NRT. A plataforma precisa proteger credenciais, limitar acessos e evitar a exposição de informações pessoais, mantendo uma implementação compatível com o escopo do MVP.

## Decisão

Adotar os seguintes controles:

* funções e políticas IAM para os principais componentes;
* princípio do menor privilégio nas permissões;
* criptografia em trânsito com HTTPS;
* criptografia dos dados armazenados nos serviços AWS;
* armazenamento da chave da API no AWS Secrets Manager;
* pseudonimização do CPF com HMAC no AWS KMS;
* proteção dos endpoints de negócio da API com AWS IAM;
* bloqueio de acesso público aos buckets;
* logs sem CPF, nome, telefone ou e-mail.

A solução utiliza endpoints gerenciados da AWS e não possui uma VPC dedicada.

## Justificativa

Os controles implementados protegem os principais pontos de acesso e os dados utilizados pelo MVP, sem adicionar a complexidade e o custo operacional de uma arquitetura de rede privada.

O uso de serviços gerenciados reduz a administração de infraestrutura e centraliza o controle de identidade, criptografia e auditoria na AWS.

## Alternativas

* **VPC dedicada com sub-redes privadas:** não implementada devido ao custo e à complexidade adicionais para o volume atual.
* **Autenticação corporativa ou Amazon Cognito:** não implementada porque a demonstração utiliza credenciais AWS IAM.
* **Chaves gerenciadas pelo cliente para todos os serviços:** não adotadas; foram utilizadas quando necessárias, como na geração do HMAC do CPF.
* **Ambientes em contas AWS separadas:** não adotados porque o MVP possui apenas o ambiente de desenvolvimento.

## Controles recomendados para produção

Em um ambiente produtivo, a segurança deveria evoluir para:

* contas separadas para desenvolvimento, homologação e produção;
* VPC dedicada, sub-redes privadas e VPC Endpoints para os serviços AWS;
* segregação mais granular de funções e políticas IAM;
* autenticação federada com um provedor corporativo de identidade;
* AWS WAF, limitação de requisições e proteção adicional da API;
* rotação automática de segredos e chaves;
* auditoria com AWS CloudTrail, AWS Config, GuardDuty e Security Hub;
* centralização e proteção contra alteração dos logs de segurança.

Esses controles não foram implementados por restrições de tempo, custo e escopo, mas são necessários antes da utilização da plataforma com dados reais de pacientes.
