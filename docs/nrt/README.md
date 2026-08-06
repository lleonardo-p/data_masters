# Fluxo NRT de Dengue

Este documento apresenta o fluxo Near Real-Time da BAIP, responsável por
transformar eventos recentes de triagem de dengue em indicadores operacionais e
históricos pseudonimizados.

Os eventos utilizados na demonstração são sintéticos e não representam
pacientes reais.

## Diagrama do processo NRT

![Arquitetura do fluxo NRT](../../architecture/c4/nrt/fluxo_nrt.drawio.svg)

## 1. Fonte dos eventos

O fluxo recebe eventos de triagem publicados por sistemas hospitalares. Cada
evento contém:

- identificadores do evento e da triagem;
- data e sistema de origem;
- CPF, idade e sexo do paciente;
- classificação do caso e nível de risco;
- data de início dos sintomas;
- unidade, município e UF do atendimento.

Para a demonstração, um simulador local produz eventos sintéticos e os publica
no Amazon SQS.

> [!NOTE]
> O simulador representa um sistema hospitalar externo. O escopo principal do
> fluxo começa no recebimento da mensagem pelo Amazon SQS.

## 2. Mensageria e processamento

O Amazon SQS desacopla o sistema hospitalar do processamento e mantém as
mensagens disponíveis durante indisponibilidades temporárias.

| Componente | Responsabilidade | Retenção |
|---|---|---:|
| Fila de Triagens | Receber os eventos que serão processados | 4 dias |
| DLQ de Triagens | Isolar mensagens que falharam repetidamente | 14 dias |

O Processador NRT, implementado com AWS Lambda, recebe lotes de até dez
mensagens e executa:

1. validação do contrato JSON;
2. normalização do CPF somente em memória;
3. pseudonimização do paciente;
4. controle de idempotência;
5. gravação do histórico;
6. atualização dos indicadores agregados.

Falhas parciais são tratadas por mensagem. Após três tentativas sem sucesso, o
evento é encaminhado para a DLQ.

## 3. Pseudonimização e persistência

O CPF é utilizado para relacionar triagens do mesmo paciente sem armazenar o
documento original nas tabelas operacionais.

```text
CPF normalizado
      ↓
HMAC-SHA-256 no AWS KMS
      ↓
cpf_fingerprint
      ↓
patient_token aleatório
      ↓
Histórico pseudonimizado
```

O HMAC é determinístico: o mesmo CPF, processado com a mesma chave protegida
pelo AWS KMS, produz o mesmo fingerprint. O material criptográfico não sai do
KMS.

O fluxo utiliza quatro tabelas no Amazon DynamoDB:

| Tabela | Finalidade | Retenção |
|---|---|---:|
| Cofre de tokens | Relacionar o fingerprint ao `patient_token` | 365 dias |
| Histórico de triagens | Armazenar os eventos pseudonimizados | 90 dias |
| Indicadores NRT | Armazenar contadores agregados por minuto | 30 dias |
| Idempotência | Impedir o processamento repetido do `event_id` | 7 dias |

As tabelas utilizam criptografia em repouso, capacidade sob demanda, TTL e
recuperação point-in-time.

> [!IMPORTANT]
> A BAIP não precisa armazenar, recuperar ou apresentar o CPF em texto aberto.
> Na consulta individual, o documento existe somente durante a requisição e é
> transformado novamente em fingerprint para localizar o histórico.

## 4. Indicadores e consumo pela API

Cada triagem atualiza indicadores agregados nos seguintes recortes:

- visão global;
- Unidade Federativa;
- município;
- unidade de atendimento;
- faixa etária.

Os indicadores são agrupados por minuto e pelos níveis de risco azul, verde,
amarelo, laranja e vermelho. Para distribuir as gravações, cada indicador
utiliza oito shards, somados no momento da consulta.

O Amazon API Gateway disponibiliza os endpoints:

| Método | Endpoint | Finalidade | Autenticação |
|---|---|---|---|
| `GET` | `/health` | Verificar a disponibilidade da API | Pública |
| `GET` | `/v1/indicators` | Consultar indicadores agregados | AWS IAM |
| `POST` | `/v1/patients/history` | Consultar o histórico pseudonimizado | AWS IAM |

### 4.1 Indicadores por UF

A consulta por UF apresenta o volume de triagens, sua evolução por minuto e a
distribuição por nível de risco.

![Indicadores NRT por Unidade Federativa](../assets/nrt-api-state.png)

### 4.2 Indicadores por faixa etária

A consulta por faixa etária permite acompanhar quais grupos aparecem com maior
frequência nas triagens recentes.

![Indicadores NRT por faixa etária](../assets/nrt-api-age-group.png)

### 4.3 Histórico do paciente

Na consulta individual, a API recebe o CPF, reproduz o fingerprint HMAC,
localiza o `patient_token` e retorna os eventos associados.

A resposta não apresenta CPF, nome, telefone, e-mail, fingerprint ou token
técnico.

![Histórico pseudonimizado do paciente](../assets/nrt-api-patient-history.png)

> Os indicadores representam sinais operacionais para investigação e
> planejamento. Eles não constituem diagnóstico médico nem confirmação
> automática de epidemia.

## 5. Confiabilidade, segurança e observabilidade

O fluxo aplica os seguintes controles:

- `event_id` e tabela de idempotência para impedir duplicidades;
- transações no DynamoDB para manter histórico e indicadores consistentes;
- falha parcial do lote e DLQ para isolar mensagens com erro;
- autenticação AWS IAM nos endpoints de negócio;
- HMAC-SHA-256 com chave protegida pelo AWS KMS;
- criptografia em repouso nas filas e tabelas;
- permissões IAM específicas por responsabilidade;
- retenção automática por TTL;
- logs sem CPF, nome, telefone ou e-mail.

O Amazon CloudWatch concentra logs, métricas e alarmes para erros das funções,
respostas `5xx`, crescimento da fila principal e presença de mensagens na DLQ.
Os alertas são encaminhados para um tópico do Amazon SNS.

> [!NOTE]
> A pseudonimização reduz a exposição dos dados, mas não equivale à
> anonimização. O acesso continua protegido por autenticação, autorização e
> criptografia.

## 6. Limites do fluxo

O fluxo NRT foi desenvolvido como um MVP para demonstrar processamento
orientado a eventos, pseudonimização, idempotência e consumo por API.

A implementação:

- utiliza exclusivamente dados sintéticos;
- não realiza diagnóstico médico;
- não confirma automaticamente uma epidemia;
- não recupera nem apresenta o CPF em texto aberto;
- não substitui sistemas hospitalares ou epidemiológicos oficiais;
- não executa automaticamente o reprocessamento da DLQ.

