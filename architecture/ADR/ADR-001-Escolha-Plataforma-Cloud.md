# ADR-001: Escolha da Plataforma Cloud

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

A BAIP precisa de um ambiente escalável e seguro para executar os fluxos Batch e Near Real-Time (NRT). A plataforma também deve favorecer o desenvolvimento rápido, reduzir o esforço operacional e permitir a integração entre serviços gerenciados.

## Decisão

Utilizar a Amazon Web Services (AWS), priorizando serviços gerenciados e serverless na região `us-east-1`.

## Justificativa

A AWS atende aos requisitos técnicos dos dois fluxos e oferece integração entre os serviços necessários para ingestão, processamento, armazenamento, segurança, observabilidade e consumo dos dados.

Além disso, é a plataforma cloud de maior domínio técnico do desenvolvedor, reduzindo a curva de aprendizado e o tempo de implementação do projeto.

## Alternativas

* **Ambiente on-premises:** não adotado devido ao maior esforço necessário para provisionamento, escalabilidade, segurança e manutenção da infraestrutura.
* **Microsoft Azure:** tecnicamente viável, mas não adotado devido à menor experiência do desenvolvedor com a plataforma.
* **Google Cloud Platform:** tecnicamente viável, mas não adotado devido à menor experiência do desenvolvedor com a plataforma.
