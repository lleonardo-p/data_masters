# Comandos do Makefile — demonstração BAIP

Este documento explica os comandos usados para demonstrar os fluxos Batch e
NRT. Execute todos os comandos a partir da raiz do repositório.

> [!IMPORTANT]
> Respeite a ordem apresentada. O Batch deve terminar com sucesso antes da
> leitura do manifesto e da execução dos testes de aceitação.

## 1. Preparar a fonte externa

### 1.1 Subir PostgreSQL e FastAPI

O comando inicia o banco PostgreSQL e a API local que representa a fonte
externa dos dados de dengue. O Docker aguarda o banco ficar saudável antes de
iniciar a API.

**COMANDO A EXECUTAR:**

```bash
make source-up
```

### 1.2 Verificar a fonte externa

Consulta o endpoint `/health` da FastAPI e mostra o estado dos contêineres da
API e do PostgreSQL.

O resultado esperado contém:

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

### 2.1 Subir o túnel HTTPS

Inicia o ngrok e cria uma URL HTTPS temporária para que a Lambda executada na
AWS consiga acessar a API local.

**COMANDO A EXECUTAR:**

```bash
make tunnel-up
```

### 2.2 Verificar a API pelo túnel

Obtém automaticamente a URL atual do ngrok e consulta o endpoint `/health` por
meio da internet. Esse teste comprova que a API está acessível pela Lambda.

**COMANDO A EXECUTAR:**

```bash
make tunnel-health
```

> [!WARNING]
> Mantenha o computador, Docker, PostgreSQL, FastAPI e ngrok ligados durante a
> extração Batch.

## 3. Executar o fluxo Batch

### 3.1 Iniciar uma carga diária

Inicia a Step Functions para extrair e processar os registros cuja data de
notificação é `2026-03-02`.

- `GRANULARITY=day`: define uma extração diária;
- `PERIOD=2026-03-02`: data de notificação consultada na API;
- `PROCESSING_DATE=2026-08-03`: data lógica da execução e das partições do lote.

A Step Functions coordena:

```text
Extração -> Staging -> Bronze -> Silver/Quarentena -> Gold
         -> Reconciliação -> Crawler -> Glue Data Catalog
```

**COMANDO A EXECUTAR:**

```bash
make batch-run \
  GRANULARITY=day \
  PERIOD=2026-03-02 \
  PROCESSING_DATE=2026-08-03
```

### 3.2 Consultar o status do Batch

Mostra o estado da execução mais recente da Step Functions, além dos horários
de início e término e de uma eventual mensagem de erro.

**COMANDO A EXECUTAR:**

```bash
make batch-status
```

### 3.3 Monitorar até o término

Consulta a execução mais recente a cada cinco minutos. O comando permanece no
terminal até a Step Functions chegar a um estado final, como `SUCCEEDED` ou
`FAILED`.

**COMANDO A EXECUTAR:**

```bash
make batch-watch
```

> [!IMPORTANT]
> Continue somente quando o estado for `SUCCEEDED`.

### 3.4 Exibir o manifesto de reconciliação

Baixa do Amazon S3 e formata o relatório `reconciliation.json` produzido para
o lote mais recente.

O relatório compara os volumes entre Bronze, Silver, Quarentena e Gold e
valida duplicidade, chaves dimensionais, medidas e integridade referencial.

**COMANDO A EXECUTAR:**

```bash
make batch-manifest
```

O resultado esperado apresenta:

```json
"status": "SUCCEEDED"
```

e todas as verificações de `checks` como `true`.

### 3.5 Executar os testes de aceitação

Executa no Amazon Athena as consultas SQL de qualidade e aceitação do produto
analítico. O script falha caso uma regra obrigatória não seja atendida.

**COMANDO A EXECUTAR:**

```bash
make batch-validate
```

## 4. Executar o fluxo NRT

### 4.1 Construir o simulador hospitalar

Constrói a imagem Docker do produtor que simula eventos de triagem hospitalar.
Esse comando prepara a imagem, mas ainda não publica mensagens.

**COMANDO A EXECUTAR:**

```bash
make hospital-build
```

### 4.2 Publicar eventos de triagem

Inicia o simulador, publica dez eventos no Amazon SQS com intervalo de três
segundos e encerra o contêiner ao final.

- `COUNT=10`: quantidade de eventos;
- `INTERVAL=3`: intervalo de três segundos entre publicações.

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

Mostra as mensagens disponíveis e em processamento na fila principal, além das
mensagens presentes na fila de erros.

**COMANDO A EXECUTAR:**

```bash
make nrt-queues
```

Após o processamento, o resultado esperado é:

- fila principal disponível: `0`;
- fila principal invisível: `0`;
- DLQ: `0`.

### 4.4 Verificar a API NRT

Consulta o endpoint público `/health` do API Gateway. Esse endpoint confirma
que a integração API Gateway e Lambda está disponível.

**COMANDO A EXECUTAR:**

```bash
make nrt-health
```

### 4.5 Consultar indicadores globais

Consulta os indicadores agregados de todas as triagens processadas nos últimos
60 minutos, incluindo totais por nível de risco e série temporal por minuto.

**COMANDO A EXECUTAR:**

```bash
make nrt-indicators \
  SCOPE_TYPE=GLOBAL \
  WINDOW_MINUTES=60
```

### 4.6 Consultar indicadores de São Paulo

Aplica o escopo `STATE` e retorna apenas os indicadores agregados associados à
UF `SP` nos últimos 60 minutos.

**COMANDO A EXECUTAR:**

```bash
make nrt-indicators \
  SCOPE_TYPE=STATE \
  SCOPE_VALUE=SP \
  WINDOW_MINUTES=60
```

O resultado pode ser zero quando nenhum dos eventos do período pertence a São
Paulo.

### 4.7 Consultar o histórico individual

Envia um CPF exclusivamente sintético para a API protegida com AWS IAM. A API:

1. normaliza o CPF;
2. gera a identidade determinística com AWS KMS HMAC;
3. resolve o token técnico do paciente;
4. consulta os eventos associados ao token no DynamoDB.

O limite padrão é de 50 eventos por página. `next_token=null` indica que não há
outra página.

**COMANDO A EXECUTAR:**

```bash
make nrt-history CPF=90088005780
```

### 4.8 Consultar logs do NRT

Exibe os logs recentes da Lambda processadora e da Lambda responsável pela API.
Os logs permitem verificar eventos inseridos, duplicados, rejeitados e falhas
técnicas sem registrar CPF, nome, telefone ou e-mail.

**COMANDO A EXECUTAR:**

```bash
make nrt-logs
```

### 4.9 Subir o dashboard NRT

Constrói e inicia o dashboard Streamlit em um contêiner local. O painel consulta
a API NRT com autenticação AWS IAM, compara os indicadores das UFs e apresenta
as dez UFs com mais triagens. As duas primeiras posições são destacadas em
vermelho.

Por padrão, o painel considera os últimos 60 minutos e atualiza os dados a cada
120 segundos.

**COMANDO A EXECUTAR:**

```bash
make nrt-dashboard-up
```

Para alterar a janela inicial ou a frequência de atualização:

```bash
make nrt-dashboard-up WINDOW_MINUTES=180 REFRESH_SECONDS=60
```

Acesse [http://localhost:8501](http://localhost:8501). Para verificar o serviço
ou acompanhar seus logs:

```bash
make nrt-dashboard-health
make nrt-dashboard-logs
```

## 5. Encerrar o ambiente local

Encerra PostgreSQL, FastAPI, ngrok e os demais contêineres locais. O comando não
destrói os recursos AWS nem remove o volume persistente do PostgreSQL.

**COMANDO A EXECUTAR:**

```bash
make down
```

## 6. Sequência resumida

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
