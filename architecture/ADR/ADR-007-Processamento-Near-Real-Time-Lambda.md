# ADR-007: Processamento dos Eventos NRT

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

Os eventos recebidos pelo Amazon SQS precisam ser validados, pseudonimizados e persistidos com baixa latência. O processamento também deve controlar duplicidades, atualizar indicadores agregados e encaminhar mensagens inválidas para novas tentativas.

## Decisão

Utilizar uma função AWS Lambda em Python, acionada automaticamente pelo Amazon SQS em lotes de até 10 mensagens.

Para cada evento, a função:

1. valida o contrato e os campos obrigatórios;
2. normaliza os dados recebidos;
3. gera ou localiza o token do paciente;
4. controla a duplicidade pelo `event_id`;
5. grava o histórico pseudonimizado;
6. atualiza os indicadores por minuto, território, unidade, faixa etária e risco;
7. informa ao SQS somente as mensagens que precisam ser processadas novamente.

Dados pessoais diretos não são incluídos nos registros operacionais ou nos logs.

## Justificativa

A AWS Lambda oferece processamento orientado a eventos, escalabilidade automática e cobrança por utilização. Sua integração nativa com SQS, DynamoDB, KMS e CloudWatch reduz o esforço operacional.

A capacidade disponível atende ao volume esperado de até aproximadamente 43 mil eventos por dia, sem necessidade de manter servidores ativos continuamente.

## Alternativas

* **Amazon ECS com Fargate:** não adotado porque exigiria gerenciamento de contêineres e capacidade ativa para uma carga intermitente.
* **Amazon Kinesis Data Analytics ou Apache Flink:** não adotado porque o fluxo não exige processamento contínuo com janelas complexas.
* **AWS Glue Streaming:** não adotado porque acrescentaria custo e complexidade para transformações de baixa latência e pequeno volume.
* **Processamento síncrono pelo sistema hospitalar:** não adotado porque aumentaria o acoplamento e faria o produtor aguardar todo o processamento.
* **Serviço executado em instância EC2:** não adotado devido à necessidade de provisionamento, atualização e monitoramento do servidor.
