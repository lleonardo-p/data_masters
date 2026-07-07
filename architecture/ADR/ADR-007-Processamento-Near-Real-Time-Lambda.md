# ADR-007: Processamento Near Real-Time com AWS Lambda

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

Eventos hospitalares simulados publicados na fila precisam ser processados com baixa latência, validação, enriquecimento leve, atualização de indicadores e persistência controlada.

A solução deve ser simples, barata e com baixa operação para o MVP.

## Decisão

O processamento near real-time será realizado com **AWS Lambda** consumindo mensagens do Amazon SQS.

A função será responsável por:

- validar schema do evento;
- aplicar idempotência por `event_id`;
- descartar ou enviar para DLQ eventos inválidos;
- atualizar agregados no DynamoDB;
- registrar métricas e logs sem PII;
- gravar eventos tratados somente quando necessário para auditoria ou reconciliação.

Para evitar problema de pequenos arquivos no S3, gravações evento a evento devem ser evitadas em produção. Quando necessário, a arquitetura deve usar compactação posterior ou serviço bufferizado.

## Justificativa

Lambda é adequada para processamento orientado a eventos, com cobrança por uso, escala automática e integração direta com SQS, DynamoDB e CloudWatch.

A decisão mantém o fluxo near real-time simples e econômico.

## Alternativas consideradas

- **AWS Glue Streaming:** mais adequado para processamento contínuo com Spark, mas mais caro e complexo.
- **Kinesis Data Analytics/Flink:** bom para streaming avançado, mas excessivo para o MVP.
- **ECS/Fargate:** útil para consumidores long-running, mas adiciona operação.
- **EMR Streaming:** alto controle, porém desnecessário para o escopo atual.

## Consequências

### Positivas

- Baixo custo para tráfego intermitente.
- Escala automática.
- Integração nativa com SQS e DynamoDB.
- Menor esforço operacional.

### Negativas

- Limites de tempo de execução e memória.
- Requer controle de concorrência.
- Pode gerar pequenos arquivos se gravar diretamente no S3 por evento.

## Critérios de evolução

Revisar esta decisão se:

- o volume de eventos exigir processamento contínuo e alto throughput;
- houver necessidade de janelas temporais complexas;
- a função atingir limites de tempo, memória ou concorrência;
- a quantidade de arquivos pequenos no Data Lake prejudicar performance e custo.

## Referências

- AWS Lambda
- Lambda event source mapping for SQS
- AWS Well-Architected Serverless Applications
