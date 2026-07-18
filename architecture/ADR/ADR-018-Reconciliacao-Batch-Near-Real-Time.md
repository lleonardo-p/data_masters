# ADR-018: Separação e Reconciliação entre Batch e Near Real-Time

- **Status:** Aceito
- **Data:** 2026-07-18
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP possui um batch baseado em notificações oficiais do SINAN/OpenDataSUS e
planeja um NRT baseado em eventos sintéticos de triagem hospitalar.

Esses eventos não possuem o mesmo grão nem representam necessariamente a mesma
população. Somá-los criaria uma falsa consolidação: triagem ou suspeita
hospitalar não equivale a notificação oficial confirmada.

## Decisão

O batch e o NRT serão produtos separados:

- **Batch dengue:** fonte oficial consolidada para análise histórica no
  `fact_dengue_cases`.
- **NRT hospitalar:** visão operacional sintética de eventos recentes servida
  por API/DynamoDB.

O dashboard deve rotular origem, atualização e caráter oficial/provisório de
cada métrica. Não será criado `official_total + nrt_delta` entre fontes sem
correspondência semântica comprovada.

A reconciliação atual ocorre dentro de cada fluxo:

- batch: Staging → Bronze → Silver/quarentena → Gold;
- NRT: recebidos → válidos/invalidados → processados/idempotentes → indicador.

Se futuramente eventos NRT forem formalmente incorporados ao sistema oficial,
um novo contrato deverá definir chave de correlação, estados, fonte de verdade,
janela, late events e precedência antes de combinar métricas.

## Justificativa

Separar os produtos evita dupla contagem e impede que uma métrica operacional
seja apresentada como estatística epidemiológica oficial. Também permite que
cada fonte mantenha qualidade, latência e finalidade apropriadas.

## Alternativas consideradas

- **Somar NRT ao batch:** rejeitado porque os grãos e processos de negócio são
  distintos.
- **Substituir o batch pelo NRT:** rejeitado porque o simulador não é fonte
  oficial.
- **Ocultar a divergência no dashboard:** rejeitado por comprometer semântica e
  governança.
- **Manter produtos separados e rotulados:** escolhido para o MVP.

## Consequências

### Positivas

- semântica clara;
- menor risco de dupla contagem;
- preserva a fonte oficial;
- SLO NRT pode evoluir sem alterar o batch;
- consumidores entendem atualização e finalidade.

### Negativas / Trade-offs

- o dashboard possui métricas separadas;
- não existe um “total em tempo real” oficial;
- correlação futura exigirá contrato e governança adicionais.

## Escalabilidade e alternativas

Reconciliações devem operar por `batch_id`, janela e partição. No NRT,
`event_id` e escrita condicional evitam efeito duplicado. Se surgir uma fonte
comum entre batch e stream, watermarks e tabela transacional podem controlar
late data e correção, mas isso altera a fonte de verdade e exige novo ADR.

## Critérios de evolução

Revisar se:

- hospitais enviarem eventos reais ao processo oficial;
- existir identificador de correlação autorizado;
- a visão NRT se tornar oficial;
- uma regulamentação definir consolidação e precedência;
- for adotado streaming stateful com correção histórica.

## Referências

- Idempotent Event Processing
- Event Time vs Processing Time
- [Lambda com SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [DynamoDB conditional operations](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)
