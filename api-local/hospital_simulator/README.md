# Simulador hospitalar NRT

Aplicação Python que gera triagens de dengue inteiramente sintéticas e publica
os eventos em uma fila Amazon SQS. O intervalo padrão é de três segundos.

O serviço não utiliza dados reais. Nomes e identificadores são criados apenas
para demonstrar o tratamento de PII no fluxo NRT. E-mails usam o domínio
reservado `example.invalid` e os telefones não são roteáveis.

## Configuração

No arquivo `api-local/.env`, configure:

```dotenv
AWS_PROFILE=baip-dev
AWS_REGION=us-east-1
NRT_SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/QUEUE_NAME
NRT_EVENT_INTERVAL_SECONDS=3
NRT_MAX_EVENTS=0
NRT_DRY_RUN=false
NRT_RANDOM_SEED=
NRT_LOG_LEVEL=INFO
```

`NRT_MAX_EVENTS=0` mantém o produtor em execução contínua. Um valor como `5`
encerra o container depois de cinco eventos e é útil para testes.

## Teste sem SQS

O modo `DRY_RUN` gera os eventos e os registra sem publicá-los:

```bash
cd api-local

NRT_DRY_RUN=true \
NRT_MAX_EVENTS=3 \
docker compose --profile nrt up --build hospital-simulator
```

Os logs mostram somente identificadores técnicos e informações operacionais.
CPF, nome, telefone e e-mail não são registrados.

## Publicação na SQS

Após configurar a URL da fila e as credenciais AWS:

```bash
cd api-local
docker compose --profile nrt up --build --detach hospital-simulator
docker compose logs --follow hospital-simulator
```

Para encerrar:

```bash
docker compose --profile nrt stop hospital-simulator
```

## Testes unitários

```bash
cd api-local/hospital_simulator
python3 -m unittest discover -s tests -v
```

O contrato JSON do evento está em
`src/contracts/nrt/triage_event_v1.schema.json`.
