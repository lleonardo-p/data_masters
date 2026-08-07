# ADR-011: Qualidade de Dados e Reconciliação

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

A conclusão técnica dos jobs não garante a qualidade dos dados. O fluxo precisa normalizar os registros, isolar dados inválidos e comprovar que não houve perda, duplicação ou inconsistência entre Bronze, Silver, Quarentena e Gold.

## Decisão

Aplicar a qualidade durante as transformações e utilizar um job independente para reconciliar os resultados.

### Bronze para Silver

O job:

* converte e padroniza tipos, datas e códigos;
* enriquece os registros com referências utilizadas pelo projeto;
* aplica regras de preenchimento e validade;
* classifica os registros como `VALID`, `WARNING` ou inválidos;
* envia registros inválidos para a Quarentena;
* preserva o motivo da rejeição, o `batch_id` e os metadados de processamento.

### Silver para Gold

O job:

* seleciona o snapshot mais recente dos casos;
* elimina duplicidades pela identidade do caso;
* cria as dimensões e a tabela fato;
* transforma os indicadores em medidas analíticas;
* mantém a granularidade de uma linha por caso na tabela fato.

### Job de reconciliação

Após a criação da Gold, um job próprio em PySpark verifica:

* identidade do lote entre as camadas;
* igualdade entre Bronze e Silver mais Quarentena;
* fechamento dos status da Silver;
* correspondência entre o snapshot da Silver e a Gold;
* correspondência dos identificadores e hashes;
* unicidade das dimensões;
* unicidade da granularidade da tabela fato;
* integridade referencial;
* validade das medidas binárias.

O job de reconciliação **não transforma, corrige ou remove dados**. Ele apenas audita os resultados e interrompe o pipeline quando uma verificação obrigatória falha.

O relatório é armazenado em JSON e a Gold somente é publicada no Glue Data Catalog após sua aprovação.

## Justificativa

A normalização na Silver cria uma representação consistente dos dados. A Quarentena evita descartes silenciosos e permite investigar registros inválidos sem bloquear os dados aceitos.

A deduplicação na Gold garante a granularidade da tabela fato. A reconciliação funciona como um **quality gate**, comprovando a consistência entre as camadas antes da publicação.

O job próprio oferece controle sobre as regras, o formato do relatório e sua integração com a Step Functions.

## Contrato de dados

As validações atuais estão implementadas diretamente nos jobs. O projeto ainda não possui um contrato de dados formal, independente e versionado.

Como evolução, o contrato poderá definir:

* campos obrigatórios;
* tipos e formatos;
* regras de nulabilidade;
* valores aceitos;
* compatibilidade entre versões do schema;
* responsáveis pelo dado e regras de evolução.

## Trade-off aceito

A Gold é reconstruída a partir do snapshot completo da Silver. Essa estratégia:

* simplifica reprocessamentos;
* mantém fatos e dimensões sincronizados;
* reduz o risco de versões conflitantes;
* facilita a reconciliação integral;
* torna a publicação idempotente.

Por outro lado, os jobs Silver para Gold e de reconciliação releem milhões de registros, aumentando duração e custo conforme o histórico cresce.

Esse comportamento é aceitável para o volume atual. Em uma evolução, o fluxo poderá utilizar processamento incremental, operações de `MERGE` e formatos de tabela como Apache Iceberg.

## Alternativas

* **Validar somente na Silver:** não adotado porque não comprovaria a consistência da Gold.
* **Consultas manuais no Athena:** não adotadas porque ocorreriam após a publicação e dependeriam de execução humana.
* **AWS Glue Data Quality:** não adotado para manter as regras integradas aos jobs do MVP.
* **Great Expectations ou Amazon Deequ:** não adotados devido às dependências e à complexidade adicionais.
* **Processamento incremental:** não adotado inicialmente por exigir controle de estado, atualização e reconciliação mais complexos.
