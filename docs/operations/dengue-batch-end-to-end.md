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

## Operação recomendada

Na raiz do repositório:

```bash
chmod +x scripts/dengue_batch.sh

./scripts/dengue_batch.sh start
./scripts/dengue_batch.sh status
./scripts/dengue_batch.sh manifest
./scripts/dengue_batch.sh validate
./scripts/dengue_batch.sh history
```

O script sempre consulta a execução mais recente para recuperar o nome real do
lote. Isso evita procurar um manifesto com uma variável `BATCH_ID` diferente da
utilizada pela Step Functions.

## Implantação

Execute da raiz do repositório:

```bash
TF_DIR="infra/terraform/environments/dev"

terraform -chdir="${TF_DIR}" fmt -recursive
terraform -chdir="${TF_DIR}" validate
terraform -chdir="${TF_DIR}" plan -out=dengue-batch.tfplan
terraform -chdir="${TF_DIR}" apply dengue-batch.tfplan
```

Na primeira implantação, o plan adiciona o job de reconciliação, o script no
bucket de artefatos, a role/policy da Step Functions, log group, state machine,
SNS topic e três alarmes. Os jobs existentes recebem o argumento `BATCH_ID`.
Em implantações posteriores, o plan deve refletir apenas mudanças reais do
código ou da infraestrutura.

Não aplique se o plan indicar destruição inesperada de buckets, databases ou
dados.

## Preparar a entrada

A implementação Bronze atual lê arquivos com extensão `.csv`. Descompacte os
ZIPs antes do upload; não envie `.zip` ou `.csv.gz` sem antes adaptar o
`pathGlobFilter` e validar a leitura.

Defina os caminhos locais:

```bash
SOURCE_DIR="/caminho/para/os/csv"
IBGE_FILE="/caminho/para/municipios_ufs_ibge.json"
TF_DIR="infra/terraform/environments/dev"

LAKE_BUCKET="$(
  terraform -chdir="${TF_DIR}" output -raw data_lake_bucket_name
)"
```

Confira os arquivos antes de enviar:

```bash
ls -lh \
  "${SOURCE_DIR}/DENGBR24.csv" \
  "${SOURCE_DIR}/DENGBR25.csv" \
  "${SOURCE_DIR}/DENGBR26.csv" \
  "${IBGE_FILE}"

shasum -a 256 \
  "${SOURCE_DIR}/DENGBR24.csv" \
  "${SOURCE_DIR}/DENGBR25.csv" \
  "${SOURCE_DIR}/DENGBR26.csv"
```

Upload para a Staging e reference:

```bash
aws s3 cp \
  "${SOURCE_DIR}/DENGBR24.csv" \
  "s3://${LAKE_BUCKET}/staging/opendatasus/dengue/reference_year=2024/DENGBR24.csv" \
  --profile baip-dev \
  --region us-east-1

aws s3 cp \
  "${SOURCE_DIR}/DENGBR25.csv" \
  "s3://${LAKE_BUCKET}/staging/opendatasus/dengue/reference_year=2025/DENGBR25.csv" \
  --profile baip-dev \
  --region us-east-1

aws s3 cp \
  "${SOURCE_DIR}/DENGBR26.csv" \
  "s3://${LAKE_BUCKET}/staging/opendatasus/dengue/reference_year=2026/DENGBR26.csv" \
  --profile baip-dev \
  --region us-east-1

aws s3 cp \
  "${IBGE_FILE}" \
  "s3://${LAKE_BUCKET}/reference/ibge/municipalities/municipios_ufs_ibge.json" \
  --profile baip-dev \
  --region us-east-1
```

Confirme os objetos:

```bash
aws s3 ls \
  "s3://${LAKE_BUCKET}/staging/opendatasus/dengue/" \
  --recursive \
  --profile baip-dev \
  --region us-east-1

aws s3 ls \
  "s3://${LAKE_BUCKET}/reference/ibge/municipalities/" \
  --profile baip-dev \
  --region us-east-1
```

Se os mesmos objetos já estiverem corretos na Staging, não é necessário
reenviá-los em toda execução.

## Execução manual equivalente

Use um nome único; Step Functions não permite reutilizar imediatamente o mesmo
nome de execução.

```bash
TF_DIR="infra/terraform/environments/dev"
STATE_MACHINE_ARN="$(
  terraform -chdir="${TF_DIR}" output -raw dengue_batch_state_machine_arn
)"
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

Forma recomendada:

```bash
./scripts/dengue_batch.sh status
```

Forma manual:

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

## Implantar as views Athena

As views não são recriadas em toda execução. Implante-as na criação do ambiente
ou quando algum SQL de `src/athena/dengue/views` mudar:

```bash
./scripts/deploy_athena_dengue_views.sh
```

O arquivo `06_vw_dengue_dashboard.sql` cria a view agregada usada pelo
consumidor QuickSight. A ativação do datasource, do dataset SPICE e do
painel está no [runbook do dashboard](quicksight-dengue-dashboard.md).

O script aguarda o término das cinco consultas DDL e falha se o Athena rejeitar
qualquer uma delas.

## Aceitação no Athena

Após a Step Functions concluir:

```bash
./scripts/dengue_batch.sh validate
```

Esse comando chama `scripts/run_athena_dengue_acceptance.sh`, executa todos os
SQLs em `src/athena/dengue/validation` e retorna erro se qualquer check produzir
`passed=false`.

## Alertas

Execuções com status `FAILED`, `TIMED_OUT` ou `ABORTED` acionam alarmes que
publicam no tópico SNS exibido por:

```bash
terraform \
  -chdir="infra/terraform/environments/dev" \
  output -raw dengue_batch_alerts_topic_arn
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

Uma execução sanitizada já validada está documentada em
[Batch de dengue — execução validada](../batch-dengue/validated-run.md).
