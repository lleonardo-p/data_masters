# ADR-008: Armazenamento Operacional do Fluxo NRT

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

O fluxo NRT precisa armazenar históricos de triagem, tokens de pacientes, controles de idempotência e indicadores agregados. As leituras e escritas devem possuir baixa latência e suportar variações no volume sem administração de servidores.

## Decisão

Utilizar o Amazon DynamoDB no modo de capacidade sob demanda, com quatro tabelas:

* **Tokens:** relaciona o fingerprint HMAC do CPF ao `patient_token`;
* **Histórico:** armazena as triagens por `patient_token` e data do evento;
* **Idempotência:** registra o `event_id` para impedir processamento duplicado;
* **Indicadores:** armazena contadores por minuto, território, unidade, faixa etária e nível de risco.

Os indicadores utilizam contadores distribuídos em shards para reduzir o risco de concentração de escritas em uma única partição.

As tabelas utilizam criptografia, recuperação point-in-time e TTL conforme a política de retenção do projeto.

## Justificativa

O DynamoDB oferece baixa latência, escalabilidade automática e integração direta com AWS Lambda. O modo sob demanda evita o provisionamento antecipado de capacidade e atende ao volume variável do NRT.

As consultas da aplicação possuem padrões conhecidos e baseados em chaves, tornando o banco chave-valor adequado ao caso.

A separação das tabelas reduz o acoplamento entre histórico, identidade, indicadores e controle de duplicidade.

## Alternativas

* **Amazon RDS ou PostgreSQL:** não adotado porque exigiria dimensionamento, conexões persistentes e maior esforço operacional.
* **Amazon S3 com Athena:** não adotado para o consumo NRT porque não oferece a mesma latência para escritas e consultas individuais.
* **Amazon ElastiCache:** não adotado porque os dados precisam permanecer disponíveis mesmo após reinicializações ou falhas do cache.
* **Amazon Timestream:** não adotado porque atenderia aos indicadores temporais, mas não substituiria as tabelas de tokens, histórico e idempotência.
* **Tabela única no DynamoDB:** não adotada para manter o modelo mais simples e facilitar a demonstração das responsabilidades de cada conjunto de dados.
