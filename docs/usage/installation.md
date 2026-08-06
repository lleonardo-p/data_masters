# Instalação e execução da BAIP

Este guia prepara o ambiente local, provisiona a infraestrutura AWS e valida
os fluxos Batch e NRT no ambiente `dev`.

Execute todos os comandos a partir da raiz do repositório.

## 1. Pré-requisitos

- Git;
- AWS CLI v2;
- Terraform `>= 1.10.0`;
- Docker com Docker Compose;
- Python 3;
- GNU Make;
- `curl`;
- conta e token do ngrok;
- conta AWS com permissão para provisionar os recursos do projeto;
- acesso à API de Localidades do IBGE.

Clone o projeto:

```bash
git clone https://github.com/lleonardo-p/data_masters.git
cd data_masters
```

## 2. Configuração local

### 2.1 Credenciais AWS

O projeto utiliza o profile `baip-dev` e a região `us-east-1`.

```bash
aws configure --profile baip-dev

export AWS_PROFILE=baip-dev
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
export TF_VAR_aws_profile=baip-dev
export TF_VAR_aws_region=us-east-1

aws sts get-caller-identity \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}"
```

Para contas com AWS IAM Identity Center, utilize `aws configure sso` e
`aws sso login` no mesmo profile.

> Nunca salve credenciais AWS no repositório.

### 2.2 Variáveis dos componentes locais

Crie o arquivo local de configuração:

```bash
cp api-local/.env.example api-local/.env
```

Edite `api-local/.env` e substitua os valores de exemplo. A mesma senha deve
ser usada em `POSTGRES_PASSWORD` e `DATABASE_URL`.

Campos obrigatórios:

- `POSTGRES_PASSWORD`: senha do PostgreSQL local;
- `DATABASE_URL`: conexão com o PostgreSQL no Docker;
- `API_KEY`: chave usada entre a Lambda Batch e a API local;
- `NGROK_AUTHTOKEN`: token obtido no painel do ngrok.

O arquivo `.env` é ignorado pelo Git e não deve ser versionado.

## 3. Provisionar a infraestrutura AWS

### 3.1 Criar o backend do Terraform

O bootstrap cria o bucket que armazena o state remoto:

```bash
terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=infra/terraform/bootstrap apply bootstrap.tfplan

export TF_STATE_BUCKET="$(
  terraform -chdir=infra/terraform/bootstrap \
    output -raw terraform_state_bucket
)"
```

Inicialize o ambiente `dev` com esse backend:

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

### 3.2 Aplicar o ambiente

```bash
make infra-plan
make infra-apply
make infra-output
```

Revise o plano antes do `apply`. Os arquivos `*.tfplan` não devem ser
versionados.

## 4. Configurações obrigatórias do Batch

### 4.1 Registrar a chave da API no Secrets Manager

A chave deve ser igual ao valor `API_KEY` de `api-local/.env`:

```bash
export SOURCE_API_KEY="$(sed -n 's/^API_KEY=//p' api-local/.env)"
export SOURCE_SECRET_NAME="$(
  terraform -chdir=infra/terraform/environments/dev \
    output -raw dengue_source_api_secret_name
)"

aws secretsmanager put-secret-value \
  --secret-id "${SOURCE_SECRET_NAME}" \
  --secret-string "${SOURCE_API_KEY}" \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}"

unset SOURCE_API_KEY
```

### 4.2 Enviar a referência do IBGE

A referência é usada pela Silver para resolver município, UF e região. Baixe
o JSON pela [API oficial de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades):

```bash
curl --fail --location \
  "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome" \
  --output municipios_ufs_ibge.json
```

Envie o arquivo para o caminho esperado pelo job:

```bash
export IBGE_FILE="$(pwd)/municipios_ufs_ibge.json"
export DATA_LAKE_BUCKET="$(
  terraform -chdir=infra/terraform/environments/dev \
    output -raw data_lake_bucket_name
)"

test -f "${IBGE_FILE}"

aws s3 cp \
  "${IBGE_FILE}" \
  "s3://${DATA_LAKE_BUCKET}/reference/ibge/municipalities/municipios_ufs_ibge.json" \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}"
```

### 4.3 Validar o ambiente

Com o Docker em execução, valide dependências, credenciais e outputs:

```bash
make check
```

## 5. Preparar a fonte histórica local

O comando abaixo baixa os arquivos oficiais de dengue de 2024, 2025 e 2026,
converte-os para `.csv.gz`, inicia PostgreSQL e FastAPI e importa os registros:

```bash
make source-setup
```

Valide a fonte:

```bash
make source-health
```

Na primeira execução, o download e a importação de milhões de registros podem
levar alguns minutos. Arquivos já preparados e importados são reaproveitados.

## 6. Executar o fluxo Batch

Exponha temporariamente a API local para a Lambda:

```bash
make tunnel-up
make tunnel-health
```

Mantenha Docker e ngrok em execução até o fim da extração.

### Carga pontual

Exemplo mensal:

```bash
make batch-run \
  GRANULARITY=month \
  PERIOD=2024-01 \
  PROCESSING_DATE="$(date -u +%F)"
```

Para uma carga diária, use `GRANULARITY=day` e `PERIOD=AAAA-MM-DD`.

### Backfill

```bash
make batch-backfill \
  GRANULARITY=month \
  START_PERIOD=2024-01 \
  END_PERIOD=2026-02 \
  PROCESSING_DATE="$(date -u +%F)"
```

### Acompanhar e validar

```bash
make batch-watch
make batch-manifest
make athena-deploy-views
make batch-validate
```

Antes de avançar, confirme:

- execução da Step Functions em `SUCCEEDED`;
- manifesto com `status: SUCCEEDED` e verificações em `true`;
- testes de aceitação do Athena aprovados.

## 7. Validar o fluxo NRT

Construa o simulador e publique eventos sintéticos de triagem:

```bash
make hospital-build
make nrt-publish COUNT=100 INTERVAL=1
```

Verifique o processamento e a API:

```bash
make nrt-queues
make nrt-health
make nrt-indicators SCOPE_TYPE=GLOBAL WINDOW_MINUTES=60
```

O resultado esperado é a fila principal sem mensagens pendentes, a DLQ vazia
e os indicadores contendo as triagens publicadas.

### Dashboard NRT

```bash
make nrt-dashboard-up WINDOW_MINUTES=60 REFRESH_SECONDS=120
make nrt-dashboard-health
```

Acesse [http://localhost:8501](http://localhost:8501).

## 8. Encerrar os componentes locais

```bash
make down
```

Esse comando encerra os contêineres locais, mas preserva os recursos AWS e o
volume do PostgreSQL.

Os demais comandos e parâmetros estão documentados em
[Comandos de demonstração](commands.md).

## Problemas frequentes

| Problema | Verificação |
|---|---|
| `.env` ausente | Crie `api-local/.env` a partir do arquivo de exemplo |
| Falha de autenticação na fonte | Confira se `API_KEY` e o segredo AWS possuem o mesmo valor |
| Túnel indisponível | Confira `NGROK_AUTHTOKEN` e execute `make tunnel-up` |
| Silver falha no enriquecimento | Confira a referência do IBGE no S3 |
| Manifesto não encontrado | Aguarde a reconciliação terminar com sucesso |
| Indicadores NRT vazios | Publique eventos recentes ou aumente `WINDOW_MINUTES` |
