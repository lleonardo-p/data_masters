# Runbook — Batch de dengue end-to-end

## Fluxo

```text
Step Functions
└── Bronze Glue
    └── Silver Glue
        └── Gold Glue
            └── Reconciliation Glue
                └── Gold Crawler
```

O nome da execução da Step Functions é o `batch_id`. Ele é propagado para as
camadas, mas não participa do `record_hash` ou `record_id`, preservando a
identidade determinística do registro.

## Implantação

```bash
cd infra/terraform/environments/dev

terraform fmt -recursive
terraform validate
terraform plan -out=dengue-batch.tfplan
terraform apply dengue-batch.tfplan
```

O plan esperado adiciona o job de reconciliação, o script no bucket de
artefatos, a role/policy da Step Functions, log group, state machine, SNS topic
e alarme. Os três jobs existentes são atualizados por causa do argumento
`BATCH_ID` e das novas versões dos scripts.

Não aplique se o plan indicar destruição inesperada de buckets, databases ou
dados.

## Iniciar o pipeline

Use um nome único; Step Functions não permite reutilizar imediatamente o mesmo
nome de execução.

```bash
STATE_MACHINE_ARN="$(terraform output -raw dengue_batch_state_machine_arn)"
BATCH_ID="dengue-$(date -u +%Y%m%dT%H%M%SZ)"

RUNNING_EXECUTIONS="$(
  aws stepfunctions list-executions \
    --state-machine-arn "${STATE_MACHINE_ARN}" \
    --status-filter RUNNING \
    --max-results 1 \
    --profile baip-dev \
    --region us-east-1 \
    --query 'length(executions)' \
    --output text
)"

if [[ "${RUNNING_EXECUTIONS}" != "0" ]]; then
  echo "Já existe uma execução ativa; não inicie snapshots concorrentes." >&2
  exit 1
fi

EXECUTION_ARN="$(
  aws stepfunctions start-execution \
    --state-machine-arn "${STATE_MACHINE_ARN}" \
    --name "${BATCH_ID}" \
    --input '{}' \
    --profile baip-dev \
    --region us-east-1 \
    --query executionArn \
    --output text
)"

echo "${EXECUTION_ARN}"
```

O bloqueio acima é operacional e suficiente para o MVP com um operador. Como
os paths atuais representam snapshots, duas execuções simultâneas poderiam
sobrescrever as mesmas partições. Em escala, substitua esse guard por lock
condicional no DynamoDB ou por escrita imutável por lote com promoção atômica
do snapshot aprovado.

## Consultar a execução

```bash
aws stepfunctions describe-execution \
  --execution-arn "${EXECUTION_ARN}" \
  --profile baip-dev \
  --region us-east-1 \
  --query 'status' \
  --output text
```

Estados finais válidos:

```text
SUCCEEDED
FAILED
TIMED_OUT
ABORTED
```

## Reconciliação

O reconciliador verifica:

- Bronze = Silver + quarentena;
- Gold = Silver;
- `valid + warning = Silver`;
- ausência de `case_id` duplicado;
- unicidade das chaves dimensionais;
- ausência de chaves órfãs;
- medidas da fato em 0/1;
- `notification_count = 1`;
- `batch_id` consistente entre as camadas.

Na igualdade de contagens, a quarentena é filtrada pelo `batch_id` atual.
Registros de execuções anteriores e registros legados sem lote são informados
separadamente no manifesto e não produzem falso desvio da execução corrente.

O manifesto é gravado em:

```text
s3://<logs-bucket>/pipeline-runs/dengue-batch/reconciliation/batch_id=<batch_id>/reconciliation.json
```

Se uma regra falhar, o manifesto é escrito com `status=FAILED`, o job falha e o
crawler não é iniciado.

## Aceitação no Athena

Após a Step Functions concluir:

```bash
chmod +x scripts/run_athena_dengue_acceptance.sh
./scripts/run_athena_dengue_acceptance.sh
```

O script executa todos os SQLs em `src/athena/dengue/validation` e retorna erro
se qualquer check produzir `passed=false`.

## Alertas

Falhas da state machine acionam o tópico SNS exibido por:

```bash
terraform output -raw dengue_batch_alerts_topic_arn
```

O tópico não possui assinatura por padrão. A assinatura deve ser criada com um
destino aprovado e confirmada antes de esperar notificações por e-mail.

## Retry

Não reinicie apenas Silver ou Gold com outro `batch_id`, pois a validação de
linhagem falhará. Corrija a causa e inicie uma nova execução completa com nome
único. O modo atual é snapshot/overwrite e foi mantido intencionalmente.

## Evidências para encerrar a execução

Preserve, sem dados pessoais ou secrets:

- saída sanitizada do `terraform plan`;
- ARN, início, fim e status da execução;
- manifesto de reconciliação;
- resultado dos cinco checks Athena;
- status da última execução do crawler;
- histórico do alarme em um teste controlado de falha.
