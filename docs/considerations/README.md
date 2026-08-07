# Considerações do projeto

A BAIP foi desenvolvida como um MVP para demonstrar uma plataforma de dados de
ponta a ponta. O escopo principal começa na ingestão pela AWS e termina na
disponibilização dos dados pelo Athena e pela API NRT.

## 1. Componentes locais

A pasta `api-local/` contém recursos utilizados somente na demonstração:

- API e PostgreSQL para disponibilizar os dados históricos;
- ngrok para exposição temporária da fonte Batch;
- simulador de triagens hospitalares;
- dashboard Streamlit para visualização do NRT.

Esses componentes representam sistemas externos e não fazem parte do núcleo
avaliativo da plataforma. Todos os dados pessoais utilizados na simulação são
sintéticos.

## 2. Limitações do MVP

O projeto prioriza serviços gerenciados e serverless para reduzir custo e
esforço operacional.

Não foram implementados:

- VPC dedicada, sub-redes privadas e VPC Endpoints;
- AWS WAF e domínio próprio para a API;
- autenticação integrada a um provedor corporativo;
- ambientes separados de desenvolvimento, homologação e produção;
- centralização de observabilidade em Prometheus ou Grafana;
- recuperação multirregional automatizada.

Os componentes utilizam IAM, criptografia, logs, métricas e alarmes. Em uma
evolução produtiva, as políticas devem ser revisadas com maior granularidade e
os recursos públicos devem ser protegidos por controles adicionais de rede.

## 3. Dados e limites de interpretação

Os dados históricos são arquivos oficiais de dengue do SINAN/DATASUS referentes
a 2024, 2025 e ao período disponível de 2026. Os dados de 2026 são parciais e
podem ser revisados pela fonte.

O fluxo NRT utiliza somente eventos sintéticos de triagem. A plataforma:

- não realiza diagnóstico médico;
- não confirma nem prevê epidemias automaticamente;
- não substitui sistemas ou indicadores oficiais;
- apresenta resultados condicionados à cobertura e à qualidade da origem.

Os indicadores devem ser interpretados como apoio à investigação
epidemiológica, à priorização territorial e à preparação da rede assistencial.

## 4. Plano de continuidade e recuperação de desastre

O plano adota uma estratégia de **warm standby** inteiramente na AWS, mantendo
`us-east-1` como região primária e `us-east-2` como região de contingência.

O cenário de referência considera até **43 mil eventos NRT por dia**. Como SQS,
Lambda, DynamoDB e API Gateway são serviços elásticos, a região secundária pode
utilizar a mesma configuração lógica da região principal. Antes de uma operação
produtiva, essa capacidade deve ser confirmada com teste de carga.

### 4.1 Objetivos de recuperação

| Fluxo | RPO alvo | RTO alvo |
|---|---:|---:|
| Batch | 24 horas | 4 horas |
| NRT e API | até 5 minutos para eventos aceitos pela AWS | até 30 minutos |

- **RPO**: perda máxima de dados admitida;
- **RTO**: tempo máximo esperado para restabelecer o serviço.

### 4.2 Proteção dos componentes

| Componente | Estratégia na AWS |
|---|---|
| Infraestrutura | Recriação da região secundária com Terraform |
| Data Lake S3 | Versionamento e replicação entre regiões |
| DynamoDB | Global Tables entre as duas regiões e PITR habilitado |
| CPF pseudonimizado | Chave HMAC multirregional no AWS KMS |
| Mensageria | SQS e DLQ secundárias com retenção de quatro dias |
| Eventos NRT | Duplicação para a fila secundária por Amazon SNS |
| Lambda e API Gateway | Recursos implantados nas duas regiões |
| Endpoint da API | Failover por Amazon Route 53 |
| Observabilidade | Alarmes do CloudWatch nas duas regiões |

A fila secundária mantém os eventos recentes enquanto seu consumidor permanece
desabilitado. Em uma falha regional, o processador secundário é habilitado e
consome o backlog. O controle de idempotência impede a persistência duplicada
dos eventos já processados na região principal.

### 4.3 Procedimento de failover

1. confirmar a indisponibilidade regional pelos alarmes do CloudWatch;
2. direcionar a API pelo Route 53 e os produtores para a SQS de `us-east-2`;
3. habilitar o mapeamento entre a SQS secundária e a Lambda Processor;
4. validar API, filas, DLQ, replicação e tabelas do DynamoDB;
5. processar o backlog e acompanhar erros e latência;
6. executar a reconciliação antes do retorno controlado à região principal.

O plano deve ser testado trimestralmente. O teste deve comprovar o RPO, o RTO,
o processamento do backlog de 43 mil eventos e a consulta pseudonimizada por
CPF na região secundária.

> O DR multirregional é uma proposta de evolução e não está provisionado no
> MVP atual.
