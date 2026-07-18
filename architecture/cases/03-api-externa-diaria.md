# Caso 3 — Ingestão diária de API externa

## Decisão de escopo

A fonte principal recomendada é a API Open-Meteo, com temperatura e
precipitação diárias por coordenadas de municípios selecionados. Ela demonstra
integração externa real, paginação/fan-out, throttling, retries, checkpoint e
freshness sem duplicar o fluxo oficial de dengue.

Uma API simulada de Zika pode ser adicionada como outro provider do mesmo
framework, mas deve ser identificada como sintética. Open-Meteo não fornece
dados de Zika; as duas fontes não devem ser misturadas na narrativa.

## Objetivo

Ingerir diariamente uma API, preservar a resposta e publicar um dataset
padronizado na Silver. Não haverá Gold nesta frente: a finalidade é demonstrar
o padrão operacional de ingestão e deixar um produto tratado disponível para
futuro enriquecimento.

## Arquitetura proposta

```text
EventBridge Scheduler
        |
Step Functions execution (run_date, provider, backfill)
        |
Lambda extractor -> API externa
        |
S3 Staging -> validação/normalização -> S3 Silver
        |
manifesto operacional + métricas + alerta
```

O Scheduler inicia uma execução diária. Step Functions controla extração,
persistência, transformação e falha. Uma SQS DLQ no Scheduler registra falhas de
entrega ao alvo; falhas do pipeline são tratadas pela state machine.

## Contrato de execução

Entrada:

```json
{
  "provider": "open_meteo",
  "run_date": "2026-07-18",
  "municipality_set": "pilot_v1",
  "is_backfill": false
}
```

Chave idempotente de escrita:

```text
staging/open_meteo/weather/extract_date=2026-07-18/run_id=<id>/response.json
silver/open_meteo/weather/reference_date=2026-07-18/
```

O manifesto registra parâmetros, quantidade de requests, status HTTP, linhas,
checksum, horário de início/fim e versão do contrato. Uma nova tentativa do
mesmo `run_date` deve ser reconhecida ou gravada em `run_id` separado, sem
sobrescrever silenciosamente uma execução anterior.

## Regras de extração

- timeout de conexão e leitura;
- retry apenas para falhas transitórias e códigos adequados;
- backoff exponencial com jitter;
- respeito a `Retry-After` e aos limites publicados pelo fornecedor;
- concorrência limitada, nunca fan-out irrestrito;
- checkpoint por município/lote;
- segredo ou API key no Secrets Manager, se a fonte exigir;
- user agent e identificação do cliente conforme termos da API;
- métricas de sucesso, erro, latência e throttle.

## Silver

Campos sugeridos:

```text
provider
reference_date
municipality_code
latitude
longitude
temperature_min_c
temperature_max_c
temperature_mean_c
precipitation_mm
timezone
source_request_id
extract_date
source_file
schema_version
silver_loaded_at
data_quality_status
```

Qualidade mínima:

- schema e versão conhecidos;
- data de referência válida;
- coordenadas e município mapeados;
- unidade explícita;
- limites físicos plausíveis como alerta ou quarentena conforme severidade;
- ausência de duplicata para `provider + municipality + reference_date`;
- freshness diária medida.

Não é obrigatório repetir a mesma quarentena do caso dengue. Para esta frente,
é suficiente falhar o lote em quebra estrutural e isolar respostas inválidas em
um prefixo técnico quando necessário.

## Lambda ou Fargate

Lambda é a primeira escolha quando a extração termina em até 15 minutos, usa
dependências leves e cabe nos limites de memória, payload e `/tmp`.

Fargate passa a ser melhor quando:

- a execução ultrapassa 15 minutos;
- bibliotecas ou binários são pesados;
- é necessário mais controle de CPU/memória;
- existem muitos lotes independentes que podem executar em paralelo;
- a conexão precisa ser mantida por mais tempo.

Uma estratégia escalável cria trabalhos por partição (por exemplo, grupo de
municípios) em SQS ou Step Functions Distributed Map e inicia tasks Fargate com
concorrência limitada. Paralelismo interno não pode ultrapassar o rate limit da
API externa.

## Rede e limites do Fargate

Cada task Fargate em `awsvpc` recebe uma ENI e um IP da subnet. Escalar tasks sem
planejar CIDR pode esgotar IPs. Em subnet privada, acesso à internet normalmente
passa por NAT Gateway, que adiciona custo e deve ser desenhado por AZ para evitar
dependência zonal. Em subnet pública, a task precisa de IP público e rota ao
Internet Gateway.

Endpoints VPC para ECR, CloudWatch, Secrets Manager e S3 reduzem tráfego pelo
NAT, mas possuem custo e não eliminam a necessidade de saída para a API pública.
Também devem ser considerados quotas de tasks concorrentes, ENIs, throughput do
NAT e conexões do fornecedor.

## Escala Multi-AZ e Multi-Region

Scheduler, Step Functions, Lambda, S3 e SQS são serviços regionais gerenciados
com resiliência interna. Tasks Fargate podem ser distribuídas em subnets de
múltiplas AZs. Isso não transforma o pipeline em Multi-Region.

Uma segunda região só é justificada por RTO/RPO ou residência definidos. Ela
exige replicação do S3, infraestrutura, secrets/keys, estado de checkpoint e
controle para impedir duas regiões de extrair e publicar o mesmo dia.

## Critério de pronto

- execução diária e backfill parametrizado;
- retry não duplica dados;
- throttle do fornecedor é respeitado;
- manifesto permite reconciliar requests e linhas;
- Silver tem schema e unidades documentados;
- falha gera alarme e runbook;
- custo por execução e duração são registrados.

## Referências

- [Open-Meteo API](https://open-meteo.com/en/docs)
- [EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html)
- [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- [Networking de tasks Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-networking.html)
- [Quotas e escala do ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/operating-at-scale-service-quotas.html)

