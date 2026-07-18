# Documentação BAIP

Este diretório organiza a documentação por fluxo de dados. Cada fluxo possui
um documento principal que descreve objetivo, arquitetura, código, operação e
estado atual.

## Fluxos

| Fluxo | Estado | Documento principal |
|---|---|---|
| Batch de dengue | Implementado e validado até o Athena | [Batch de dengue ponta a ponta](batch-dengue/README.md) |
| Triagem hospitalar near real-time | Arquitetura definida; implementação posterior | [Caso NRT](cases/02-nrt-triagem-hospitalar.md) |
| API externa diária | Arquitetura definida; implementação posterior | [Caso de ingestão diária](cases/03-api-externa-diaria.md) |

## Batch de dengue

Use os documentos nesta ordem:

1. [Visão ponta a ponta](batch-dengue/README.md): documento canônico do fluxo.
2. [Cenário de negócio](cases/01-batch-dengue.md): por que o arquivo chega manualmente.
3. [Contrato técnico](data/dengue/README.md): campos, regras e modelo Gold.
4. [Runbook operacional](operations/dengue-batch-end-to-end.md): comandos de deploy, execução e diagnóstico.
5. [Execução validada](batch-dengue/validated-run.md): contagens e verificações reproduzíveis.
6. [Dashboard QuickSight](operations/quicksight-dengue-dashboard.md).

## Segurança

- [Acesso, privacidade e PII](security/access-control-and-pii.md)
- [ADR de segurança e governança](../architecture/ADR/ADR-004-Seguranca-Governanca-Dados.md)
- [ADR de qualidade](../architecture/ADR/ADR-011-Qualidade-Dados.md)

## Decisões de arquitetura

As decisões e seus trade-offs estão em [`architecture/ADR`](../architecture/ADR/).
Os diagramas editáveis e suas exportações estão em
[`architecture/c4`](../architecture/c4/).
