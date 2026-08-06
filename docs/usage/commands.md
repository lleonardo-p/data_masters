# Comandos do Makefile â€” demonstraÃ§Ã£o BAIP

Este documento explica os comandos usados para demonstrar os fluxos Batch e
NRT. Execute todos os comandos a partir da raiz do repositÃ³rio.

> [!IMPORTANT]
> Respeite a ordem apresentada. O Batch deve terminar com sucesso antes da
> leitura do manifesto e da execuÃ§Ã£o dos testes de aceitaÃ§Ã£o.

## 1. Preparar a fonte externa

### 1.1 Subir PostgreSQL e FastAPI

O comando inicia o banco PostgreSQL e a API local que representa a fonte
externa dos dados de dengue. O Docker aguarda o banco ficar saudÃ¡vel antes de
iniciar a API.

**COMANDO A EXECUTAR:**

```bash
make source-up
```

### 1.2 Verificar a fonte externa

Consulta o endpoint `/health` da FastAPI e mostra o estado dos contÃªineres da
API e do PostgreSQL.

O resultado esperado contÃ©m:

```json
{
  "status": "up",
  "database": "up"
}
```

**COMANDO A EXECUTAR:**

```bash
make source-health
```

## 2. Publicar a API local com ngrok

### 2.1 Subir o tÃºnel HTTPS

Inicia o ngrok e cria uma URL HTTPS temporÃ¡ria para que a Lambda executada na
AWS consiga acessar a API local.

**COMANDO A EXECUTAR:**

```bash
make tunnel-up
```

### 2.2 Verificar a API pelo tÃºnel

ObtÃ©m automaticamente a URL atual do ngrok e consulta o endpoint `/health` por
meio da internet. Esse teste comprova que a API estÃ¡ acessÃ­vel pela Lambda.

**COMANDO A EXECUTAR:**

```bash
make tunnel-health
```

> [!WARNING]
> Mantenha o computador, Docker, PostgreSQL, FastAPI e ngrok ligados durante a
> extraÃ§Ã£o Batch.

## 3. Executar o fluxo Batch

### 3.1 Iniciar uma carga diÃ¡ria

Inicia a Step Functions para extrair e processar os registros cuja data de
notificaÃ§Ã£o Ã© `2026-03-02`.

- `GRANULARITY=day`: define uma extraÃ§Ã£o diÃ¡ria;
- `PERIOD=2026-03-02`: data de notificaÃ§Ã£o consultada na API;
- `PROCESSING_DATE=2026-08-03`: data lÃ³gica da execuÃ§Ã£o e das partiÃ§Ãµes do lote.

A Step Functions coordena:

```text
ExtraÃ§Ã£o -> Staging -> Bronze -> Silver/Quarentena -> Gold
         -> ReconciliaÃ§Ã£o -> Crawler -> Glue Data Catalog
```

**COMANDO A EXECUTAR:**

```bash
make batch-run \
  GRANULARITY=day \
  PERIOD=2026-03-02 \
  PROCESSING_DATE=2026-08-03
```

### 3.2 Consultar o status do Batch

Mostra o estado da execuÃ§Ã£o mais recente da Step Functions, alÃ©m dos horÃ¡rios
de inÃ­cio e tÃ©rmino e de uma eventual mensagem de erro.

**COMANDO A EXECUTAR:**

```bash
make batch-status
```

### 3.3 Monitorar atÃ© o tÃ©rmino

Consulta a execuÃ§Ã£o mais recente a cada cinco minutos. O comando permanece no
terminal atÃ© a Step Functions chegar a um estado final, como `SUCCEEDED` ou
`FAILED`.

**COMANDO A EXECUTAR:**

```bash
make batch-watch
```

> [!IMPORTANT]
> Continue somente quando o estado for `SUCCEEDED`.

### 3.4 Exibir o manifesto de reconciliaÃ§Ã£o

Baixa do Amazon S3 e formata o relatÃ³rio `reconciliation.json` produzido para
o lote mais recente.

O relatÃ³rio compara os volumes entre Bronze, Silver, Quarentena e Gold e
valida duplicidade, chaves dimensionais, medidas e integridade referencial.

**COMANDO A EXECUTAR:**

```bash
make batch-manifest
```

O resultado esperado apresenta:

```json
"status": "SUCCEEDED"
```

e todas as verificaÃ§Ãµes de `checks` como `true`.

### 3.5 Executar os testes de aceitaÃ§Ã£o

Executa no Amazon Athena as consultas SQL de qualidade e aceitaÃ§Ã£o do produto
analÃ­tico. O script falha caso uma regra obrigatÃ³ria nÃ£o seja atendida.

**COMANDO A EXECUTAR:**

```bash
make batch-validate
```

## 4. Executar o fluxo NRT

### 4.1 Construir o simulador hospitalar

ConstrÃ³i a imagem Docker do produtor que simula eventos de triagem hospitalar.
Esse comando prepara a imagem, mas ainda nÃ£o publica mensagens.

**COMANDO A EXECUTAR:**

```bash
make hospital-build
```

### 4.2 Publicar eventos de triagem

Inicia o simulador, publica dez eventos no Amazon SQS com intervalo de trÃªs
segundos e encerra o contÃªiner ao final.

- `COUNT=10`: quantidade de eventos;
- `INTERVAL=3`: intervalo de trÃªs segundos entre publicaÃ§Ãµes.

**COMANDO A EXECUTAR:**

```bash
make nrt-publish COUNT=10 INTERVAL=3
```

Os eventos seguem este fluxo:

```text
Simulador -> SQS -> Lambda Processor -> KMS HMAC
          -> DynamoDB -> API Gateway/Lambda API
```

### 4.3 Verificar a fila principal e a DLQ

Mostra as mensagens disponÃ­veis e em processamento na fila principal, alÃ©m das
mensagens presentes na fila de erros.

**COMANDO A EXECUTAR:**

```bash
make nrt-queues
```

ApÃ³s o processamento, o resultado esperado Ã©:

- fila principal disponÃ­vel: `0`;
- fila principal invisÃ­vel: `0`;
- DLQ: `0`.

### 4.4 Verificar a API NRT

Consulta o endpoint pÃºblico `/health` do API Gateway. Esse endpoint confirma
que a integraÃ§Ã£o API Gateway e Lambda estÃ¡ disponÃ­vel.

**COMANDO A EXECUTAR:**

```bash
make nrt-health
```

### 4.5 Consultar indicadores globais

Consulta os indicadores agregados de todas as triagens processadas nos Ãºltimos
60 minutos, incluindo totais por nÃ­vel de risco e sÃ©rie temporal por minuto.

**COMANDO A EXECUTAR:**

```bash
make nrt-indicators \
  SCOPE_TYPE=GLOBAL \
  WINDOW_MINUTES=60
```

### 4.6 Consultar indicadores de SÃ£o Paulo

Aplica o escopo `STATE` e retorna apenas os indicadores agregados associados Ã 
UF `SP` nos Ãºltimos 60 minutos.

**COMANDO A EXECUTAR:**

```bash
make nrt-indicators \
  SCOPE_TYPE=STATE \
  SCOPE_VALUE=SP \
  WINDOW_MINUTES=60
```

O resultado pode ser zero quando nenhum dos eventos do perÃ­odo pertence a SÃ£o
Paulo.

### 4.7 Consultar o histÃ³rico individual

Envia um CPF exclusivamente sintÃ©tico para a API protegida com AWS IAM. A API:

1. normaliza o CPF;
2. gera a identidade determinÃ­stica com AWS KMS HMAC;
3. resolve o token tÃ©cnico do paciente;
4. consulta os eventos associados ao token no DynamoDB.

O limite padrÃ£o Ã© de 50 eventos por pÃ¡gina. `next_token=null` indica que nÃ£o hÃ¡
outra pÃ¡gina.

**COMANDO A EXECUTAR:**

```bash
make nrt-history CPF=90088005780
```

### 4.8 Consultar logs do NRT

Exibe os logs recentes da Lambda processadora e da Lambda responsÃ¡vel pela API.
Os logs permitem verificar eventos inseridos, duplicados, rejeitados e falhas
tÃ©cnicas sem registrar CPF, nome, telefone ou e-mail.

**COMANDO A EXECUTAR:**

```bash
make nrt-logs
```

### 4.9 Subir o dashboard NRT

ConstrÃ³i e inicia o dashboard Streamlit em um contÃªiner local. O painel consulta
a API NRT com autenticaÃ§Ã£o AWS IAM, compara os indicadores das UFs e apresenta
as dez UFs com mais triagens. As duas primeiras posiÃ§Ãµes sÃ£o destacadas em
vermelho.

Por padrÃ£o, o painel considera os Ãºltimos 60 minutos e atualiza os dados a cada
120 segundos.

**COMANDO A EXECUTAR:**

```bash
make nrt-dashboard-up
```

Para alterar a janela inicial ou a frequÃªncia de atualizaÃ§Ã£o:

```bash
make nrt-dashboard-up WINDOW_MINUTES=180 REFRESH_SECONDS=60
```

Acesse [http://localhost:8501](http://localhost:8501). Para verificar o serviÃ§o
ou acompanhar seus logs:

```bash
make nrt-dashboard-health
make nrt-dashboard-logs
```

## 5. Encerrar o ambiente local

Encerra PostgreSQL, FastAPI, ngrok e os demais contÃªineres locais. O comando nÃ£o
destrÃ³i os recursos AWS nem remove o volume persistente do PostgreSQL.

**COMANDO A EXECUTAR:**

```bash
make down
```

## 6. SequÃªncia resumida

```bash
make source-up
make source-health

make tunnel-up
make tunnel-health

make batch-run \
  GRANULARITY=day \
  PERIOD=2026-03-02 \
  PROCESSING_DATE=2026-08-03

make batch-status
make batch-watch
make batch-manifest
make batch-validate

make hospital-build
make nrt-publish COUNT=10 INTERVAL=3
make nrt-queues
make nrt-health

make nrt-indicators \
  SCOPE_TYPE=GLOBAL \
  WINDOW_MINUTES=60

make nrt-indicators \
  SCOPE_TYPE=STATE \
  SCOPE_VALUE=SP \
  WINDOW_MINUTES=60

make nrt-history CPF=90088005780
make nrt-logs
make nrt-dashboard-up
make nrt-dashboard-health
make down
```