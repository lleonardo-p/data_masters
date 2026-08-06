# Instalação e execução da plataforma

Este guia provisiona o ambiente `dev`, carrega os arquivos necessários e
executa o fluxo Batch de dengue até as views e validações no Athena.

Execute os comandos a partir da raiz do repositório.

## 1. Pré-requisitos

- Git;
- AWS CLI v2;
- Terraform `>= 1.10.0`;
- Docker com Docker Compose;
- Python 3;
- uma conta AWS com permissão para criar S3, IAM, Glue, Athena, Step Functions,
  CloudWatch e SNS;
- o arquivo de referência `municipios_ufs_ibge.json`.

Verifique as ferramentas:

```bash
aws --version
terraform version
```

## 2. Configurar a credencial AWS

O projeto utiliza por padrão o profile `baip-dev` e a região `us-east-1`.

### Opção recomendada: AWS IAM Identity Center

```bash
aws configure sso --profile baip-dev
aws sso login --profile baip-dev
```

### Alternativa: credencial de acesso

Se a conta não utilizar IAM Identity Center:

```bash
aws configure --profile baip-dev
```

Informe o Access Key ID, o Secret Access Key, `us-east-1` e o formato `json`
quando solicitado.

> Nunca salve chaves AWS no repositório, em arquivos `.tfvars`, scripts ou
> documentação. O profile deve permanecer em `~/.aws/`, fora do Git.

Defina as variáveis usadas pelos comandos e pelo Terraform:

```bash
export AWS_PROFILE="baip-dev"
export AWS_REGION="us-east-1"
export AWS_DEFAULT_REGION="us-east-1"
export TF_VAR_aws_profile="${AWS_PROFILE}"
export TF_VAR_aws_region="${AWS_REGION}"
```

Valide a sessão e capture o ID da conta:

```bash
aws sts get-caller-identity \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}"

export AWS_ACCOUNT_ID="$(
  aws sts get-caller-identity \
    --profile "${AWS_PROFILE}" \
    --region "${AWS_REGION}" \
    --query Account \
    --output text
)"

echo "${AWS_ACCOUNT_ID}"
```

O resultado deve ser um ID numérico de 12 dígitos. Se o comando falhar, corrija
a autenticação antes de executar o Terraform.

## 3. Criar o state remoto do Terraform

O diretório `infra/terraform/bootstrap` cria o bucket S3 que armazena o state
remoto. O bootstrap possui state local porque ele cria o próprio backend.

```bash
terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap fmt -check
terraform -chdir=infra/terraform/bootstrap validate
terraform -chdir=infra/terraform/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=infra/terraform/bootstrap apply bootstrap.tfplan
```

Capture o bucket criado:

```bash
export TF_STATE_BUCKET="$(
  terraform -chdir=infra/terraform/bootstrap \
    output -raw terraform_state_bucket
)"

echo "${TF_STATE_BUCKET}"
```

O bucket segue o padrão:

```text
baip-dev-terraform-state-<AWS_ACCOUNT_ID>
```

Ele possui bloqueio de acesso público, versionamento e criptografia SSE-S3. O
backend utiliza o lockfile nativo do S3 (`use_lockfile = true`) para impedir
alterações simultâneas no state.

### Inicializar o ambiente com o backend remoto

O `backend.tf` versionado representa o ambiente original do projeto. Os
parâmetros abaixo sobrescrevem conta e profile durante a inicialização, evitando
usar por engano o bucket de outra conta:

```bash
terraform -chdir=infra/terraform/environments/dev init \
  -reconfigure \
  -backend-config="bucket=${TF_STATE_BUCKET}" \
  -backend-config="key=environments/dev/terraform.tfstate" \
  -backend-config="region=${AWS_REGION}" \
  -backend-config="profile=${AWS_PROFILE}" \
  -backend-config="encrypt=true" \
  -backend-config="use_lockfile=true"
```

Confirme que o state remoto está acessível:

```bash
terraform -chdir=infra/terraform/environments/dev state list
```

Na primeira instalação, a lista pode estar vazia. Isso é esperado.

## 4. Provisionar a infraestrutura

Formate, valide e gere um plano salvo:

```bash
terraform -chdir=infra/terraform/environments/dev fmt -check
terraform -chdir=infra/terraform/environments/dev validate
terraform -chdir=infra/terraform/environments/dev plan -out=baip-dev.tfplan
```

Revise o resumo do plano. Em uma instalação nova, serão criados buckets, roles,
jobs Glue, databases do catálogo, crawler, workgroup Athena, Step Functions,
logs, alarmes e tópico SNS.

Depois da revisão, aplique exatamente o plano aprovado:

```bash
terraform -chdir=infra/terraform/environments/dev apply baip-dev.tfplan
```

`terraform apply baip-dev.tfplan` executa o plano previamente revisado.
`terraform apply` sem o arquivo calcula um novo plano no momento da execução.

Arquivos `*.tfplan` podem conter valores da infraestrutura e estão ignorados
pelo Git; não devem ser commitados.

Consulte os recursos e paths criados:

```bash
terraform -chdir=infra/terraform/environments/dev output
```

Capture o bucket do Data Lake:

```bash
export DATA_LAKE_BUCKET="$(
  terraform -chdir=infra/terraform/environments/dev \
    output -raw data_lake_bucket_name
)"

echo "${DATA_LAKE_BUCKET}"
```

## 5. Enviar a referência de municípios do IBGE

A Silver utiliza essa referência para converter códigos SINAN/IBGE e resolver
município, UF e região.

Defina o caminho local do arquivo:

```bash
export IBGE_FILE="/caminho/para/municipios_ufs_ibge.json"
test -f "${IBGE_FILE}"
```

Envie-o para o path esperado pelo job:

```bash
aws s3 cp \
  "${IBGE_FILE}" \
  "s3://${DATA_LAKE_BUCKET}/reference/ibge/municipalities/municipios_ufs_ibge.json" \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}"
```

Valide o objeto:

```bash
aws s3 ls \
  "s3://${DATA_LAKE_BUCKET}/reference/ibge/municipalities/" \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}"
```

## 6. Preparar a fonte externa local

O projeto automatiza a preparação da fonte histórica utilizada pela API local.
Execute:

```bash
make source-setup
```

Esse comando:

1. baixa `DENGBR24.csv.zip`, `DENGBR25.csv.zip` e `DENGBR26.csv.zip` do
   Portal de Dados Abertos do SUS;
2. valida os arquivos ZIP;
3. converte cada CSV para o formato `.csv.gz` esperado pelo importador;
4. inicia o PostgreSQL e a FastAPI com Docker Compose;
5. importa os registros no banco;
6. verifica a disponibilidade da fonte.

Os arquivos são armazenados em `api-local/data/`, diretório ignorado pelo Git.
Downloads e importações já concluídos são ignorados nas próximas execuções.

Para executar somente o download e a conversão:

```bash
make source-download
```

Valide a fonte externa:

```bash
make source-health
```

> [!NOTE]
> O download e a importação inicial processam milhões de registros e podem
> levar alguns minutos, dependendo da conexão e dos recursos disponíveis para
> o Docker.

## 7. Executar o fluxo Batch

O script `dengue_batch.sh` consulta os outputs do Terraform e impede o início de
uma segunda execução enquanto outra estiver em `RUNNING`.

Inicie a Step Functions:

```bash
./scripts/dengue_batch.sh start
```

O script gera um identificador no formato:

```text
dengue-YYYYMMDDTHHMMSSZ
```

Consulte o estado da execução mais recente:

```bash
./scripts/dengue_batch.sh status
```

Consulte o histórico:

```bash
./scripts/dengue_batch.sh history
```

O pipeline executa:

```text
Bronze -> Silver/Quarentena -> Gold -> Reconciliação -> Crawler
```

Espere o status `SUCCEEDED` antes das próximas etapas. A execução pode levar
dezenas de minutos, dependendo do volume e da capacidade disponível no Glue.

### Consultar o manifesto de reconciliação

```bash
./scripts/dengue_batch.sh manifest
```

O manifesto deve apresentar `"status": "SUCCEEDED"` e todos os itens de
`checks` como `true`.

Para consultar um lote específico:

```bash
export BATCH_ID="dengue-YYYYMMDDTHHMMSSZ"
./scripts/dengue_batch.sh manifest
unset BATCH_ID
```

## 8. Criar as views do Athena

Depois que o pipeline e o crawler terminarem com sucesso, execute:

```bash
./scripts/deploy_athena_dengue_views.sh
```

O script executa os arquivos de `src/athena/dengue/views/` em ordem e espera o
Athena concluir cada comando. O resultado esperado é:

```text
All dengue analytical views were deployed successfully.
```

## 9. Executar os testes de aceitação

Use o comando integrado:

```bash
./scripts/dengue_batch.sh validate
```

Ele chama `run_athena_dengue_acceptance.sh` e verifica:

- unicidade do grão da fato;
- consistência do `batch_id`;
- medidas binárias;
- chaves das dimensões;
- coerência dos totais analíticos.

O resultado esperado é:

```text
All Athena dengue acceptance checks passed.
```

## 10. Conferência final no Athena

No editor do Athena, selecione:

- fonte de dados: `AwsDataCatalog`;
- database: `baip_dev_gold`;
- workgroup: `baip-dev-workgroup`.

Liste os objetos:

```sql
SHOW TABLES IN baip_dev_gold;
```

Consulte uma view analítica:

```sql
SELECT
    notification_year,
    notification_month,
    SUM(notification_count) AS notifications,
    SUM(confirmed_case_count) AS confirmed_cases,
    SUM(hospitalized_case_count) AS hospitalized_cases,
    SUM(death_by_disease_count) AS deaths
FROM baip_dev_gold.vw_dengue_cases_enriched
GROUP BY
    notification_year,
    notification_month
ORDER BY
    notification_year,
    notification_month;
```

## Sequência resumida

```text
1. Autenticar na AWS
2. Criar o bucket de state remoto
3. Inicializar e aplicar o Terraform do ambiente dev
4. Enviar a referência IBGE
5. Enviar os três CSVs para a Staging
6. Executar dengue_batch.sh start
7. Aguardar SUCCEEDED e consultar o manifesto
8. Executar deploy_athena_dengue_views.sh
9. Executar dengue_batch.sh validate
10. Consultar as views no Athena
```

## Solução rápida de problemas

| Erro | Verificação |
|---|---|
| `Invalid endpoint: https://glue..amazonaws.com` | Confirme `AWS_REGION` e `AWS_DEFAULT_REGION` |
| `Invalid bucket name ""` | Refaça o `terraform output` e confira `DATA_LAKE_BUCKET` |
| `NoRegion` | Exporte `AWS_REGION=us-east-1` |
| `PATH_NOT_FOUND` | Confira os paths e se os uploads terminaram |
| Bronze não encontra arquivos | Confirme que os objetos terminam em `.csv` |
| Silver falha no enriquecimento | Confira o JSON IBGE no path de referência |
| Manifesto retorna `404` | Aguarde a reconciliação ou informe o `BATCH_ID` correto |
| Athena não mostra tabelas | Aguarde o crawler concluir e atualize o catálogo no console |
| O script não inicia outro lote | Existe uma execução `RUNNING`; consulte `history` e `status` |
