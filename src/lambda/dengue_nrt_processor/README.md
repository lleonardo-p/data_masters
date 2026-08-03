# Processador NRT de triagens de dengue

Lambda acionada pela fila SQS de triagens sintéticas. A função valida o
contrato, pseudonimiza o CPF com HMAC no AWS KMS, controla duplicidade e grava
somente dados pseudonimizados ou agregados no DynamoDB.

## Persistência

| Tabela | Finalidade | Retenção |
|---|---|---:|
| `dengue-patient-tokens` | Mapeia `HMAC(CPF)` para `patient_token` | 365 dias |
| `dengue-triage-history` | Histórico individual sem identificadores diretos | 90 dias |
| `dengue-nrt-indicators` | Contadores operacionais por minuto | 30 dias |
| `dengue-nrt-idempotency` | Impede a contagem repetida de `event_id` | 7 dias |

O TTL executa a limpeza assíncrona do DynamoDB e não deve ser tratado como
expurgo imediato. Uma solicitação de expurgo deverá executar deleção explícita
e auditada nas tabelas aplicáveis.

## Privacidade

O CPF é normalizado somente em memória e enviado ao KMS para geração de HMAC.
O material da chave não sai do KMS. CPF, nome, telefone e e-mail não são
gravados no histórico, nos indicadores ou nos logs.

O repositório de tokens contém somente o fingerprint HMAC, o token aleatório e
metadados técnicos. Como a associação pode ser refeita mediante CPF e acesso à
chave, o processo representa pseudonimização, não anonimização.

## Idempotência

O histórico, o registro de idempotência e os contadores são atualizados em uma
transação DynamoDB. Uma condição sobre `event_id` impede que uma entrega
duplicada do SQS incremente novamente os indicadores.

## Escalabilidade

Cada dimensão dos indicadores usa oito shards de escrita. Isso evita concentrar
todos os eventos de uma UF ou do indicador global em uma única chave lógica. A
API de leitura deverá somar os oito shards ao consultar um intervalo.

## Testes

```bash
python3 -m unittest discover \
  -s src/lambda/dengue_nrt_processor/tests \
  -v
```
