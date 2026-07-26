# Lambda Dengue Batch Extractor

Extrai registros da API externa de dengue e grava a resposta compactada na
Staging do Amazon S3. A funÃ§Ã£o Ã© invocada manualmente nesta etapa; nenhum
agendamento EventBridge Ã© provisionado.

## Evento mensal

```json
{
  "api_base_url": "https://example.ngrok-free.dev",
  "granularity": "month",
  "reference_period": "2024-01",
  "processing_date": "2026-07-26",
  "force": false
}
```

## Evento diÃ¡rio

```json
{
  "api_base_url": "https://example.ngrok-free.dev",
  "granularity": "day",
  "reference_period": "2024-01-01",
  "processing_date": "2026-07-26",
  "force": false
}
```

`processing_date` Ã© opcional e assume a data UTC da execuÃ§Ã£o. `force=false`
ignora uma extraÃ§Ã£o que jÃ¡ possua `manifest.json`. Use `force=true` somente
para reprocessar e substituir o mesmo perÃ­odo.

## Layout na Staging

```text
staging/opendatasus/dengue/
â””â”€â”€ processing_date=YYYY-MM-DD/
    â””â”€â”€ granularity=month|day/
        â””â”€â”€ reference_period=YYYY-MM|YYYY-MM-DD/
            â”œâ”€â”€ dengue.jsonl.gz
            â””â”€â”€ manifest.json
```

O manifesto registra contagem de linhas, bytes compactados, SHA-256, ETag,
perÃ­odo consultado e duraÃ§Ã£o. Sua existÃªncia funciona como marcador de
conclusÃ£o do lote.

## SeguranÃ§a

A URL Ã© recebida no evento porque o endereÃ§o gratuito do ngrok pode mudar.
A API key Ã© lida do AWS Secrets Manager e nÃ£o deve ser enviada no evento,
gravada no cÃ³digo ou incluÃ­da no Terraform state.

O host da API deve usar HTTPS e terminar em `.ngrok-free.app` ou
`.ngrok-free.dev`.

## Testes

```bash
python3 -m unittest discover \
  -s src/lambda/dengue_batch_extractor/tests \
  -v
```