# ADR-019: Plano Conceitual de Recuperação de Desastre

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

A BAIP está implantada somente na região `us-east-1`. Uma indisponibilidade regional, exclusão acidental ou corrupção de dados poderia interromper os fluxos Batch e NRT.

O volume atual não justifica uma arquitetura ativa em múltiplas regiões, mas a plataforma precisa possuir uma estratégia conceitual de recuperação dentro da AWS.

## Decisão

Adotar conceitualmente uma estratégia de **backup e restauração em uma região secundária**.

A região secundária não permanecerá com todos os serviços ativos. Em caso de desastre, a infraestrutura será recriada com Terraform e os dados serão restaurados a partir de cópias mantidas na AWS.

### Metas propostas

| Fluxo |          RPO |         RTO |
| ----- | -----------: | ----------: |
| Batch | Até 24 horas | Até 8 horas |
| NRT   |   Até 1 hora | Até 4 horas |

O Batch aceita um RPO maior porque os dados públicos podem ser extraídos e reprocessados. O NRT exige uma recuperação mais rápida devido à natureza operacional dos indicadores.

## Controles existentes

O projeto já possui:

* infraestrutura declarada com Terraform;
* código-fonte e scripts versionados;
* versionamento nos buckets S3;
* recuperação point-in-time no DynamoDB;
* reconciliação do fluxo Batch;
* DLQ para falhas no processamento NRT.

Esses controles ajudam na recuperação, mas não protegem isoladamente contra uma indisponibilidade regional.

## Controles conceituais de DR

Uma implementação produtiva deverá incluir:

* replicação dos objetos S3 para uma região secundária;
* cópias regionais dos backups do DynamoDB;
* chave KMS disponível na região de recuperação;
* replicação controlada dos segredos;
* estado remoto do Terraform protegido e disponível;
* pacotes das funções e scripts armazenados fora da região principal;
* procedimento de reenvio dos eventos não processados;
* testes periódicos de restauração.

O SQS não deve ser tratado como armazenamento permanente. Em caso de perda de mensagens durante um desastre, o sistema produtor deverá permitir o reenvio dos eventos, mantendo o mesmo `event_id` para preservar a idempotência.

## Procedimento de recuperação

Em caso de desastre:

1. declarar a indisponibilidade da região principal;
2. interromper novos acionamentos;
3. aplicar o Terraform na região secundária;
4. restaurar os objetos do S3 e as tabelas DynamoDB;
5. disponibilizar as chaves, segredos e artefatos;
6. atualizar os endereços utilizados pelos produtores e consumidores;
7. validar filas, funções, API, catálogo e permissões;
8. executar a reconciliação do Batch;
9. solicitar o reenvio dos eventos NRT pendentes;
10. liberar novamente a plataforma.

## Justificativa

A estratégia de backup e restauração possui menor custo do que manter duas regiões ativas continuamente.

O Terraform reduz o tempo necessário para recriar os recursos. O reprocessamento dos dados públicos simplifica a recuperação do Batch, enquanto backups e reenvio idempotente protegem o NRT.

Essa abordagem é compatível com o volume e o objetivo atual do projeto.

## Limitação atual

O plano é conceitual. Não foram implementados:

* replicação entre regiões;
* failover automático;
* ambiente secundário ativo;
* cópias regionais automatizadas;
* testes de recuperação.

O versionamento do S3 e o point-in-time recovery do DynamoDB protegem contra falhas lógicas, mas não representam, isoladamente, um plano completo de desastre regional.

## Alternativas

* **Arquitetura ativa-ativa em duas regiões:** não adotada devido ao custo e à complexidade.
* **Warm standby:** não adotado porque manteria recursos ativos sem necessidade para a carga atual.
* **Recuperação somente na região principal:** não adotada conceitualmente porque não cobre uma indisponibilidade regional.
* **Ausência de plano de DR:** não adotada porque impediria definir responsabilidades, prioridades e ordem de recuperação.
