# ADR-013: Acionamento do Fluxo Batch

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

O fluxo Batch precisa permitir cargas pontuais e backfills por dia ou mês. No MVP, a fonte de dados é uma API local exposta temporariamente pelo ngrok e não permanece disponível continuamente.

Uma execução automática poderia iniciar o processamento quando a fonte estivesse indisponível ou gerar execuções e custos desnecessários durante o período de demonstração.

## Decisão

Manter o acionamento manual da AWS Step Functions por meio dos comandos de demonstração do projeto.

A execução informa:

* modo pontual ou backfill;
* granularidade diária ou mensal;
* período ou intervalo de períodos;
* data de processamento;
* endereço atual da API;
* opção de reprocessamento.

A Step Functions continua responsável por orquestrar todas as etapas após o acionamento.

## Justificativa

O acionamento manual oferece controle sobre o período processado, garante que a API e o túnel estejam disponíveis e evita a execução desnecessária dos jobs AWS Glue.

O principal custo evitado não é o EventBridge, mas os serviços iniciados automaticamente por ele durante a execução completa do pipeline.

Essa abordagem também facilita demonstrações, testes e reprocessamentos controlados.

## Evolução com Amazon EventBridge

O Amazon EventBridge poderá iniciar a Step Functions automaticamente em uma periodicidade definida.

Essa evolução é recomendada quando:

* a API de origem possuir endereço estável;
* a fonte estiver disponível continuamente;
* existir uma frequência operacional definida;
* houver monitoramento e tratamento para períodos sem dados;
* o processamento recorrente fizer parte da operação da plataforma.

O agendamento automático é tecnicamente compatível com a arquitetura atual, mas não foi implementado no MVP.

## Alternativas

* **Amazon EventBridge Scheduler:** não adotado no MVP devido à disponibilidade temporária da fonte e ao risco de iniciar processamentos desnecessários.
* **Evento de criação no Amazon S3:** não adotado porque a extração começa em uma API e não pela chegada direta de um arquivo ao bucket.
* **Acionamento direto dos jobs AWS Glue:** não adotado porque ignoraria a extração, a ordem das etapas e o controle centralizado da Step Functions.
* **Acionamento direto da Lambda:** não adotado porque iniciaria apenas a extração e não representaria a execução completa do pipeline.
