# ADR-006: Mensageria do Fluxo NRT

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

O fluxo NRT precisa receber eventos de triagem hospitalar, absorver variações no volume e desacoplar os sistemas produtores do processamento. A solução deve suportar até aproximadamente 43 mil eventos por dia, com tentativas automáticas e isolamento de mensagens com falha.

## Decisão

Utilizar uma fila Amazon SQS Standard integrada à Lambda processadora.

A configuração inclui:

* entrega de mensagens em lotes de até 10;
* criptografia gerenciada pelo SQS;
* tempo de visibilidade de 180 segundos;
* retenção de mensagens por quatro dias;
* DLQ para mensagens que falharem após três tentativas;
* processamento idempotente pelo `event_id`.

## Justificativa

O Amazon SQS atende ao volume esperado com baixo custo e sem administração de servidores. Sua integração com AWS Lambda permite processamento automático, controle de retentativas e redirecionamento de falhas para a DLQ.

A fila Standard utiliza entrega pelo menos uma vez e não garante ordenação global. Essas características são aceitáveis porque os eventos possuem identificador único e o processamento implementa idempotência.

## Alternativas

* **Amazon Kinesis Data Streams:** não adotado porque o fluxo não exige ordenação por partição, retenção prolongada ou reprodução contínua dos eventos.
* **Amazon MSK ou Apache Kafka:** não adotado devido ao maior custo e esforço operacional para o volume atual.
* **Amazon EventBridge:** não adotado como fila principal porque o caso exige controle explícito de mensagens pendentes, visibilidade, retentativas e DLQ.
* **Chamada direta da Lambda:** não adotada porque aumentaria o acoplamento com o sistema hospitalar e reduziria a capacidade de absorver picos.
* **Amazon SNS:** não adotado porque o fluxo possui apenas um consumidor principal e precisa manter mensagens até seu processamento.
