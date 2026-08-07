# ADR-016: Retenção, Lifecycle e Expurgo de Dados

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

A BAIP armazena dados públicos no fluxo Batch e dados pessoais sintéticos pseudonimizados no fluxo NRT.

A retenção indefinida aumentaria custos e contrariaria o princípio de manter dados pessoais somente pelo tempo necessário. A plataforma também precisa considerar a remoção do histórico quando solicitada por um paciente.

## Decisão

Aplicar retenção conforme a finalidade de cada componente.

### Controles implementados

* TTL nas tabelas operacionais do DynamoDB pelo atributo `expires_at`;
* retenção limitada das mensagens no SQS e na DLQ;
* retenção configurada para os logs do CloudWatch;
* recuperação point-in-time nas tabelas do DynamoDB;
* versionamento nos buckets S3.

No MVP, o histórico NRT utiliza retenção aproximada de 90 dias.

### Controles conceituais para o Data Lake

As políticas automáticas de lifecycle do Amazon S3 ainda não foram implementadas.

Em uma evolução, deverão ser aplicadas para:

* excluir arquivos antigos da Staging;
* remover snapshots anteriores da Silver;
* manter a Quarentena somente durante o período de investigação;
* expirar versões anteriores da Gold;
* remover resultados antigos do Athena;
* preservar relatórios de reconciliação por um prazo maior;
* transferir dados públicos de auditoria para classes de armazenamento mais econômicas.

No fluxo Batch, o expurgo tem finalidade principalmente financeira e operacional, pois os dados processados são públicos.

## Solicitação de remoção por um paciente

A remoção individual está definida conceitualmente, mas não possui endpoint automatizado no MVP.

Após a validação da identidade e da autorização do solicitante, o processo deverá:

1. normalizar o CPF informado;
2. gerar o fingerprint HMAC no AWS KMS;
3. localizar o `patient_token` no cofre de tokens;
4. excluir todos os eventos associados ao token na tabela de histórico;
5. excluir a associação entre o fingerprint e o token;
6. registrar a conclusão do expurgo sem armazenar o CPF;
7. impedir que uma restauração de backup recupere permanentemente os dados removidos.

Os indicadores agregados poderão permanecer porque não armazenam CPF, token ou outra informação que permita identificar diretamente o paciente.

O cofre de tokens não deve remover o token antes do histórico. Caso contrário, os eventos permaneceriam armazenados sem uma chave de busca para localizá-los e excluí-los.

## Backups e recuperação

A recuperação point-in-time protege contra exclusões acidentais, mas não substitui a política de retenção.

Dados removidos podem permanecer recuperáveis durante a janela de backup. Caso uma restauração seja realizada, os expurgos registrados deverão ser reaplicados antes da liberação do ambiente.

## Justificativa

O TTL reduz armazenamento desnecessário sem exigir um processo periódico de exclusão. As retenções do SQS, DLQ e CloudWatch limitam a permanência de mensagens e logs operacionais.

A separação entre dados públicos, históricos pseudonimizados e indicadores agregados permite aplicar prazos diferentes conforme a finalidade e a sensibilidade.

O lifecycle do S3 permanece como melhoria porque o ambiente atual é um MVP e não executa cargas contínuas.

## Alternativas

* **Retenção indefinida:** não adotada devido ao aumento contínuo de custo e exposição de dados.
* **Exclusão imediata após o processamento:** não adotada porque impediria auditoria, investigação e reprocessamento.
* **Expurgo exclusivamente manual:** aceitável no MVP, mas inadequado para uma operação produtiva devido ao risco de falhas e ausência de rastreabilidade.
* **Arquivamento permanente de todas as camadas:** não adotado porque snapshots completos e versões antigas possuem baixo valor operacional.
* **Remoção apenas pelo TTL:** não adotada como solução para solicitações individuais porque o paciente não deve depender do vencimento natural do registro.
