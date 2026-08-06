# Fluxo NRT de Dengue

Este documento apresenta o fluxo Near Real-Time da BAIP, responsável por
processar eventos recentes de triagem relacionados a casos suspeitos de dengue.

O fluxo transforma eventos hospitalares em indicadores operacionais por
território, unidade, faixa etária e nível de risco. Também mantém um histórico
pseudonimizado que pode ser consultado por profissionais autorizados.

Os eventos utilizados na demonstração são sintéticos e não representam
pacientes reais.

## Diagrama do processo NRT

![Arquitetura do fluxo NRT](../../architecture/c4/nrt/fluxo_nrt.drawio.svg)

## 1. Fonte de eventos hospitalares

O fluxo NRT recebe eventos de triagem publicados por sistemas hospitalares. Cada evento representa o registro de uma triagem relacionada a um caso suspeito de dengue.

Para a demonstração, foi criado um simulador local que gera eventos sintéticos e os publica no Amazon SQS em intervalos configuráveis.

> [!NOTE]
> O simulador representa um sistema hospitalar externo e não faz parte do núcleo avaliativo da plataforma. O escopo do fluxo NRT começa no recebimento da mensagem pelo Amazon SQS.

O contrato contém:

* identificadores do evento e da triagem;
* data e sistema de origem;
* dados pessoais necessários para identificação;
* idade e sexo;
* classificação e nível de risco;
* data de início dos sintomas;
* unidade, município e UF do atendimento.

Exemplo simplificado:

```json
{
  "event_id": "4f34e36b-61f2-4c72-9255-4fc76d0bb682",
  "event_type": "TRIAGE_REGISTERED",
  "schema_version": "1.0",
  "event_time": "2026-08-03T17:06:49Z",
  "source_system": "hospital_system",
  "triage_id": "TRIAGE-20260803-a1f6e831607d",
  "patient": {
    "cpf": "00000000000",
    "full_name": "Paciente Sintético",
    "age": 32,
    "sex": "F",
    "phone": "+5500000000000",
    "email": "paciente@example.invalid"
  },
  "triage": {
    "notification_at": "2026-08-03T17:06:49Z",
    "disease_code": "A90",
    "case_classification": "SUSPECTED",
    "risk_level": "YELLOW",
    "symptoms_start_date": "2026-08-01"
  },
  "health_unit": {
    "unit_id": "CNES-SIM-0001",
    "unit_name": "Hospital Municipal Simulado",
    "municipality_code": "3550308",
    "municipality_name": "São Paulo",
    "state": "SP"
  }
}
```

Os níveis de risco aceitos são:

* `BLUE`;
* `GREEN`;
* `YELLOW`;
* `ORANGE`;
* `RED`.

Os dados pessoais permanecem no evento somente até o processamento. CPF, nome, telefone e e-mail não são propagados para o histórico pseudonimizado nem para os indicadores operacionais.


## 2. Mensageria com Amazon SQS

O Amazon SQS recebe os eventos publicados pelos sistemas hospitalares e desacopla a origem do processamento. Dessa forma, uma indisponibilidade temporária da Lambda não exige que o produtor aguarde ou reenvie imediatamente o evento.

O fluxo utiliza duas filas:

| Fila             | Finalidade                                 | Retenção |
| ---------------- | ------------------------------------------ | -------: |
| Fila de Triagens | Receber os eventos que serão processados   |   4 dias |
| DLQ de Triagens  | Reter mensagens que falharam repetidamente |  14 dias |

A fila principal utiliza:

* criptografia gerenciada pelo Amazon SQS;
* comunicação obrigatória por HTTPS;
* *long polling* para reduzir consultas vazias;
* tempo de visibilidade de 180 segundos;
* tamanho máximo de 256 KB por mensagem.

A Lambda recebe mensagens em lotes de até dez eventos. Quando apenas alguns eventos falham, somente esses itens retornam à fila para uma nova tentativa.

Após três tentativas sem sucesso, a mensagem é encaminhada para a DLQ.

```text
Sistema Hospitalar
        ↓
Fila de Triagens
        ↓
Processador NRT

Falha após três tentativas
        ↓
DLQ de Triagens
```

Como o Amazon SQS oferece entrega pelo menos uma vez, uma mensagem pode ser recebida mais de uma vez. O controle de idempotência impede que eventos repetidos gerem novos históricos ou incrementem novamente os indicadores.

> [!IMPORTANT]
> Os eventos podem conter dados pessoais enquanto permanecem nas filas. Por isso, o acesso é restrito por IAM, o transporte inseguro é bloqueado e os dados são protegidos com criptografia em repouso.

## 3. Processamento com AWS Lambda

A fila de triagens é integrada a uma função AWS Lambda responsável por validar, pseudonimizar e persistir os eventos.

A integração processa:

* lotes de até dez mensagens;
* janela máxima de dois segundos para formação do lote;
* até cinco execuções concorrentes;
* falhas parciais por mensagem.

O processamento de cada evento segue esta ordem:

1. interpretar o conteúdo JSON;
2. validar o contrato da triagem;
3. normalizar o CPF somente em memória;
4. solicitar ao AWS KMS o fingerprint HMAC do CPF;
5. obter ou criar o `patient_token`;
6. registrar o controle de idempotência;
7. gravar o histórico pseudonimizado;
8. atualizar os indicadores agregados;
9. registrar o resultado nos logs.

O histórico, a idempotência e os indicadores são atualizados em uma transação do DynamoDB. Isso evita que apenas parte do evento seja persistida.

Quando o `event_id` já foi processado, a transação não cria outro histórico nem incrementa novamente os indicadores. O evento é registrado como duplicado e considerado concluído.

Quando uma mensagem apresenta contrato inválido ou falha técnica, a Lambda informa somente aquele item como não processado. As demais mensagens válidas do mesmo lote não precisam ser executadas novamente.

```text
Lote recebido
     ↓
Validação individual
     ↓
Pseudonimização
     ↓
Transação no DynamoDB
     ↓
Evento inserido ou identificado como duplicado
```

Os logs utilizam apenas identificadores técnicos, como `message_id` e `event_id`. CPF, nome, telefone e e-mail não são registrados.

## 4. Pseudonimização do CPF

O CPF é utilizado para relacionar diferentes triagens ao mesmo paciente sem armazenar o documento original nas tabelas operacionais.

O processo utiliza dois identificadores:

| Identificador     | Finalidade                                             |
| ----------------- | ------------------------------------------------------ |
| `cpf_fingerprint` | Resultado determinístico do HMAC aplicado ao CPF       |
| `patient_token`   | Identificador técnico aleatório utilizado no histórico |

O processamento ocorre desta forma:

```text
CPF
 ↓
Normalização e validação
 ↓
HMAC-SHA-256 no AWS KMS
 ↓
cpf_fingerprint
 ↓
Cofre de Tokens
 ↓
patient_token
 ↓
Histórico de Triagens
```

A mesma combinação de CPF e chave HMAC sempre produz o mesmo fingerprint. Isso permite localizar o token do paciente sem armazenar o CPF original.

A chave criptográfica permanece protegida pelo AWS KMS. A Lambda envia o CPF normalizado para a operação `GenerateMac`, mas o material da chave não sai do serviço.

O `patient_token` é criado aleatoriamente pela aplicação. O AWS KMS gera o fingerprint, mas não gera o token.

### 4.1 Motivo para utilizar HMAC

Um hash simples de CPF seria determinístico, mas poderia ser testado por meio de uma lista de documentos possíveis.

O HMAC combina o CPF com uma chave secreta protegida pelo KMS. Dessa forma, não é possível reproduzir os fingerprints sem autorização para utilizar a chave.

### 4.2 Exemplo de pseudonimização

O exemplo abaixo utiliza um CPF exclusivamente sintético:

```text
CPF recebido
900.433.096-82
        ↓
CPF normalizado
90043309682
        ↓
HMAC-SHA-256 gerado pelo AWS KMS
7f4b2c9e8a1d6f30...3b9d7c5e1f8264ab
        ↓
Cofre de Tokens
7f4b2c9e8a1d6f30...3b9d7c5e1f8264ab
        ↓
pt_92d0c5cf42dc49ce96a977b4e102eaac
```

O fingerprint foi abreviado apenas para facilitar a leitura. Na implementação, ele é armazenado como uma sequência hexadecimal completa.

O Cofre de Tokens armazena a associação:

```json
{
  "cpf_fingerprint": "7f4b2c9e8a1d6f30...3b9d7c5e1f8264ab",
  "patient_token": "pt_92d0c5cf42dc49ce96a977b4e102eaac",
  "hmac_key_version": "v1"
}
```

O histórico utiliza somente o token técnico:

```json
{
  "patient_token": "pt_92d0c5cf42dc49ce96a977b4e102eaac",
  "triage_id": "TRIAGE-20260803-a1f6e831607d",
  "risk_level": "YELLOW",
  "state": "SP",
  "age_group": "30-39"
}
```

CPF, nome, telefone e e-mail não são gravados no histórico nem nos indicadores.

### 4.3 Consulta do histórico

Quando um profissional autorizado consulta o histórico:

1. a API recebe o CPF;
2. normaliza e valida o documento em memória;
3. solicita ao KMS o mesmo fingerprint HMAC;
4. localiza o `patient_token` no Cofre de Tokens;
5. consulta os eventos associados ao token;
6. retorna o histórico sem CPF, nome, telefone ou e-mail.

```text
CPF consultado
      ↓
Mesmo fingerprint HMAC
      ↓
patient_token correspondente
      ↓
Histórico pseudonimizado
```

Esse processo representa pseudonimização, não anonimização. A associação com o paciente pode ser refeita quando existe o CPF e autorização para utilizar a chave HMAC.

> [!NOTE]
> A BAIP não precisa recuperar, armazenar ou apresentar o CPF em texto aberto. Na consulta individual, o profissional autorizado informa o CPF, que é normalizado e transformado em um fingerprint HMAC para localizar o token e o histórico correspondente. O documento existe apenas durante o processamento da requisição e não é persistido nem incluído na resposta.
>
> A recuperação reversível do CPF permanece fora do escopo do projeto.


## 5. Persistência no Amazon DynamoDB

O fluxo NRT utiliza quatro tabelas no Amazon DynamoDB, cada uma com uma responsabilidade específica.

| Tabela                   | Chave principal                    | Finalidade                                        | Retenção |
| ------------------------ | ---------------------------------- | ------------------------------------------------- | -------: |
| Cofre de tokens          | `cpf_fingerprint`                  | Relacionar o fingerprint HMAC ao `patient_token`  | 365 dias |
| Histórico de triagens    | `patient_token` + `event_sort_key` | Armazenar o histórico pseudonimizado do paciente  |  90 dias |
| Indicadores NRT          | `scope_key` + `minute_bucket`      | Armazenar contadores agregados por minuto         |  30 dias |
| Controle de idempotência | `event_id`                         | Impedir o processamento duplicado do mesmo evento |   7 dias |

As tabelas utilizam capacidade sob demanda, criptografia em repouso, recuperação point-in-time e expiração automática por TTL.

### 5.1 Gravação transacional

Depois da validação e da pseudonimização, o Processador NRT executa uma transação que:

1. registra o `event_id` no controle de idempotência;
2. grava a triagem no histórico do paciente;
3. atualiza os indicadores agregados.

A transação evita que apenas parte dessas operações seja concluída. Se uma gravação falhar, as demais alterações relacionadas ao evento também são canceladas.

### 5.2 Retenção e recuperação

O TTL remove automaticamente registros que ultrapassaram o período de retenção definido para cada tabela.

A remoção por TTL é assíncrona e pode ocorrer algum tempo depois da data de expiração. Por isso, o TTL representa uma política de ciclo de vida e não um mecanismo de exclusão imediata.

A recuperação point-in-time permite restaurar uma tabela para um estado anterior em caso de exclusão acidental, erro de aplicação ou gravação incorreta.

> [!NOTE]
> A implementação atual não precisa recuperar ou apresentar o CPF em texto aberto. O CPF informado em uma consulta existe apenas durante o processamento da requisição e não é persistido no histórico nem nos indicadores.

### Evidência das tabelas

<!--
Adicionar uma captura das quatro tabelas no Amazon DynamoDB.
-->

![Tabelas NRT no Amazon DynamoDB](assets/dynamodb-nrt-tables.png)

---

## 6. Indicadores operacionais

Cada triagem atualiza indicadores agregados em cinco recortes:

| Escopo         | Exemplo           | Utilização                   |
| -------------- | ----------------- | ---------------------------- |
| `GLOBAL`       | Todas as triagens | Visão geral dos atendimentos |
| `STATE`        | `SP`              | Comparação entre UFs         |
| `MUNICIPALITY` | `3550308`         | Monitoramento municipal      |
| `UNIT`         | `CNES-SIM-0001`   | Acompanhamento por unidade   |
| `AGE_GROUP`    | `20-29`           | Análise por faixa etária     |

Os registros são agrupados por minuto e nível de risco:

* azul;
* verde;
* amarelo;
* laranja;
* vermelho.

Para distribuir as atualizações, cada indicador possui oito shards. O Processador NRT escolhe um shard para cada evento, reduzindo a concentração de gravações em uma única chave.

Durante uma consulta, o Serviço de Consulta NRT lê e soma os oito shards para apresentar o total consolidado.

A resposta contém:

* quantidade total de triagens;
* distribuição por nível de risco;
* série temporal por minuto;
* período e escopo consultados.

> Os indicadores representam sinais operacionais recentes. Eles não constituem diagnóstico médico nem confirmação automática de epidemia.

### Evidência dos indicadores

<!--
Adicionar uma captura da tabela de indicadores ou da resposta da API.
-->

![Indicadores agregados do fluxo NRT](assets/nrt-indicators.png)

---

## 7. Consumo pela API NRT

O Amazon API Gateway disponibiliza os endpoints e encaminha as requisições para o Serviço de Consulta NRT.

| Método | Endpoint               | Finalidade                           | Autenticação |
| ------ | ---------------------- | ------------------------------------ | ------------ |
| `GET`  | `/health`              | Verificar a disponibilidade da API   | Pública      |
| `GET`  | `/v1/indicators`       | Consultar indicadores agregados      | AWS IAM      |
| `POST` | `/v1/patients/history` | Consultar o histórico pseudonimizado | AWS IAM      |

### 7.1 Consulta de indicadores

O endpoint de indicadores recebe o escopo e o período desejado.

Exemplo:

```http
GET /v1/indicators?scope_type=STATE&scope_value=SP&window_minutes=60
```

A consulta retorna os totais e a evolução das triagens por minuto.

```json
{
  "scope_type": "STATE",
  "scope_value": "SP",
  "totals": {
    "total_triages": 25,
    "risk_green": 11,
    "risk_yellow": 9,
    "risk_orange": 4,
    "risk_red": 1
  }
}
```

### 7.2 Consulta do histórico

O histórico individual é consultado por meio de uma requisição autenticada.

```http
POST /v1/patients/history
```

```json
{
  "cpf": "90043309682",
  "limit": 50
}
```

A aplicação:

1. normaliza o CPF recebido;
2. reproduz o fingerprint com o AWS KMS;
3. localiza o `patient_token`;
4. consulta o histórico associado;
5. remove campos técnicos antes de responder.

A resposta não contém CPF, nome, telefone, e-mail, fingerprint ou token técnico.

```json
{
  "found": true,
  "events": [
    {
      "event_time": "2026-08-03T17:36:31Z",
      "unit_name": "Unidade de Saúde Simulada Sul",
      "municipality_name": "Brasília",
      "state": "DF",
      "age_group": "80+",
      "risk_level": "ORANGE",
      "case_classification": "SUSPECTED"
    }
  ],
  "next_token": null
}
```

O campo `next_token` permite consultar outra página quando a quantidade de eventos ultrapassa o limite solicitado. O valor `null` indica que não existem outras páginas.

### 7.3 Visualização de demonstração

Um dashboard local em Streamlit consome a API e apresenta as UFs com maior número de triagens, destacando as primeiras posições e a distribuição por nível de risco.

Esse dashboard é um componente de apoio à demonstração e não faz parte do núcleo do fluxo NRT implantado na AWS.

![Monitoramento NRT de triagens](../assets/baip-indicadores-NRT.png)

---

## 8. Confiabilidade do processamento

O fluxo foi projetado considerando a entrega de mensagens pelo menos uma vez. Isso significa que o Amazon SQS pode entregar novamente uma mensagem quando o processamento não é confirmado.

Os seguintes controles evitam inconsistências:

| Controle                 | Responsabilidade                                   |
| ------------------------ | -------------------------------------------------- |
| `event_id`               | Identificar unicamente o evento                    |
| Tabela de idempotência   | Impedir a gravação repetida                        |
| Transação do DynamoDB    | Manter histórico e indicadores consistentes        |
| Resposta parcial do lote | Reprocessar somente mensagens com falha            |
| Visibility Timeout       | Evitar consumo simultâneo durante o processamento  |
| DLQ                      | Isolar mensagens que falharam após três tentativas |

Quando um `event_id` já processado é recebido novamente, o evento é classificado como duplicado. O histórico e os indicadores não são alterados.

Mensagens inválidas ou que continuam falhando são encaminhadas para a DLQ, onde permanecem disponíveis para análise e eventual reprocessamento.

### Evidência de idempotência

<!--
Adicionar uma captura dos logs com um evento inserido e o mesmo evento
identificado como duplicado.
-->

![Controle de idempotência](assets/nrt-idempotency.png)

### Evidência da DLQ

<!--
Adicionar uma captura da fila principal e da DLQ.
-->

![Fila principal e DLQ](assets/nrt-sqs-dlq.png)

---

## 9. Segurança e proteção dos dados

O fluxo aplica os seguintes controles:

* autenticação AWS IAM nos endpoints de negócio;
* pseudonimização determinística do CPF com HMAC-SHA-256;
* chave HMAC protegida pelo AWS KMS;
* uso de um token aleatório como identificador do paciente;
* criptografia em repouso nas filas e tabelas;
* permissões IAM específicas para cada função;
* ausência de CPF, nome, telefone e e-mail nos históricos e indicadores;
* ausência de dados pessoais nos logs da aplicação;
* retenção limitada por TTL.

Os dados pessoais recebidos na mensagem permanecem temporariamente na fila até o processamento. Durante a execução, são utilizados apenas em memória para validação e pseudonimização.

Somente os dados necessários para análise e acompanhamento são persistidos.

> [!IMPORTANT]
> A pseudonimização reduz a exposição dos dados, mas não equivale à anonimização. O acesso aos recursos continua protegido por políticas IAM, criptografia e controles de retenção.

---

## 10. Observabilidade

O Amazon CloudWatch concentra logs, métricas e alarmes do fluxo NRT.

Os logs permitem acompanhar:

* eventos processados;
* eventos duplicados;
* mensagens rejeitadas;
* erros do Processador NRT;
* erros do Serviço de Consulta;
* duração e consumo de memória das funções.

Os logs não registram CPF, nome, telefone ou e-mail.

### 10.1 Alarmes configurados

| Alarme                       | Condição monitorada                            |
| ---------------------------- | ---------------------------------------------- |
| Erros do Processador NRT     | Falhas na Lambda que consome a fila            |
| Erros do Serviço de Consulta | Falhas na Lambda responsável pela API          |
| Erros `5xx` da API           | Respostas com falha interna                    |
| Backlog da fila              | Mil ou mais mensagens aguardando processamento |
| Mensagens na DLQ             | Existência de mensagem na fila de erros        |

Quando um alarme é acionado, o CloudWatch publica o evento em um tópico do Amazon SNS. O tópico representa o canal de notificação, mas a configuração de uma assinatura é necessária para que uma pessoa ou sistema receba o alerta.

Os grupos de logs possuem retenção configurada de 30 dias.

### Evidência dos logs

<!--
Adicionar uma captura dos logs do Processador NRT no CloudWatch.
-->

![Logs do Processador NRT](assets/cloudwatch-nrt-processor-logs.png)

### Evidência dos alarmes

<!--
Adicionar uma captura dos alarmes do fluxo NRT.
-->

![Alarmes do fluxo NRT](assets/cloudwatch-nrt-alarms.png)

---

## 11. Limites do fluxo

O fluxo NRT foi desenvolvido como um MVP para demonstrar processamento orientado a eventos, proteção de dados pessoais, idempotência e disponibilização de indicadores por API.

Os eventos utilizados são sintéticos e o sistema hospitalar é representado por um simulador local.

A plataforma:

* não utiliza dados reais de pacientes;
* não realiza diagnóstico médico;
* não confirma automaticamente uma epidemia;
* não precisa recuperar ou apresentar o CPF em texto aberto;
* não substitui sistemas hospitalares ou epidemiológicos oficiais;
* não implementa a exclusão individual sob solicitação;
* não implementa um processo de reprocessamento automático da DLQ.

Esses pontos representam limites conscientes do MVP e podem ser tratados em uma evolução para produção.
