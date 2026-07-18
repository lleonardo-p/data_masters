# Batch de dengue — execução validada

Este documento registra uma execução reproduzível do pipeline sem incluir
credenciais, state Terraform, dados brutos ou identificadores de conta AWS.

## Identificação

| Campo | Valor |
|---|---|
| Ambiente | `dev` |
| Data | 2026-07-18 |
| Batch | `dengue-20260718T144715Z` |
| Manifesto | `SUCCEEDED` |
| Aceitação Athena | 5 de 5 checks aprovados |

## Reconciliação entre camadas

| Métrica | Registros |
|---|---:|
| Bronze | 8.617.612 |
| Silver | 8.553.989 |
| Quarentena do lote | 63.623 |
| Gold fato | 8.553.989 |
| Silver `valid` | 5.652.824 |
| Silver `warning` | 2.901.165 |

Fechamento:

```text
8.617.612 = 8.553.989 + 63.623
8.553.989 = 5.652.824 + 2.901.165
Gold = Silver = 8.553.989
```

A quarentena representa aproximadamente 0,74% da Bronze. O dado não foi
descartado: registros bloqueados permanecem disponíveis para investigação fora
do produto Gold.

## Checks do manifesto

| Check | Resultado |
|---|---|
| Identidade do batch consistente | `true` |
| Bronze = Silver + quarentena | `true` |
| Chaves dimensionais únicas | `true` |
| Grão da fato único | `true` |
| Medidas da fato válidas | `true` |
| Chaves estrangeiras válidas | `true` |
| Gold = Silver | `true` |
| Status Silver fecha | `true` |

Resultados adicionais:

```text
duplicate_cases = 0
invalid_measure_rows = 0
batch_identity_mismatches = 0 em Bronze, Silver e Gold
dimension_duplicate_keys = 0 em todas as dimensões
orphan_foreign_keys = 0 em todos os papéis
quarantine_other_batches = 0
quarantine_legacy_without_batch_id = 0
```

## Checks Athena

O script `scripts/run_athena_dengue_acceptance.sh` executou:

```text
fact_grain_is_unique                  PASS
batch_identity_is_consistent         PASS
fact_measures_are_binary             PASS
core_dimension_keys_are_valid        PASS
metric_totals_are_sane               PASS
```

Cada SQL está versionado em `src/athena/dengue/validation/`. O script não cria
uma tabela: ele executa os `SELECT`, lê a coluna `passed` e retorna código
diferente de zero se algum check falhar.

## Como reproduzir

```bash
./scripts/dengue_batch.sh start
./scripts/dengue_batch.sh status
./scripts/dengue_batch.sh manifest
./scripts/dengue_batch.sh validate
```

O histórico das consultas pode ser conferido no Athena Workgroup
`baip-dev-workgroup`. O manifesto original permanece no bucket operacional de
logs, particionado pelo `batch_id`.

