# API NRT de dengue

API serverless para consultar indicadores agregados e o histórico
pseudonimizado das triagens processadas pelo fluxo NRT.

## Rotas

| Método | Rota | Autorização | Finalidade |
|---|---|---|---|
| `GET` | `/health` | Pública | Verifica a disponibilidade da API |
| `GET` | `/v1/indicators` | AWS IAM | Soma os shards dos indicadores em uma janela |
| `POST` | `/v1/patients/history` | AWS IAM | Localiza o token por CPF e consulta o histórico |

O CPF é recebido somente no corpo da requisição de histórico, normalizado em
memória e transformado em HMAC pelo KMS. A API não grava nem retorna o CPF.

## Consulta de indicadores

```text
GET /v1/indicators?scope_type=STATE&scope_value=SP&window_minutes=2
```

Também é possível informar `start` e `end` em ISO-8601. A janela máxima
automática é de 1.440 minutos.

## Consulta de histórico

```json
{
  "cpf": "900.433.096-82",
  "limit": 50
}
```

A paginação usa o campo opaco `next_token` retornado pela própria API.

## Segurança

As rotas de negócio usam assinatura AWS Signature Version 4 por meio da
autorização `AWS_IAM` do API Gateway. Em produção, o consumidor deve possuir
somente `execute-api:Invoke` nas rotas necessárias. Para usuários finais, a
evolução recomendada é um autorizador JWT com identidade corporativa e escopos.

## Testes

```bash
python3 -m unittest discover \
  -s src/lambda/dengue_nrt_api/tests \
  -v
```
