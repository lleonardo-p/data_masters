# ADR-018: Reconciliacao Batch Near Real Time

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

A BAIP possui dois fluxos relacionados à dengue:

* **Batch:** utiliza notificações públicas oficiais disponibilizadas pelo Ministério da Saúde;
* **NRT:** utiliza eventos sintéticos de triagem produzidos pelo simulador hospitalar.

As fontes não compartilham CPF, identificador do caso, identificador da triagem ou outra chave que permita relacionar os registros de forma confiável.

## Decisão

Manter os fluxos Batch e NRT independentes, sem sincronização ou reconciliação entre seus registros.

O fluxo Batch demonstra processamento histórico, qualidade, quarentena, modelagem dimensional e consumo pelo Athena.

O fluxo NRT demonstra mensageria, processamento orientado a eventos, pseudonimização, idempotência, indicadores recentes e consumo por API.

Os resultados podem ser apresentados como visões complementares do domínio, mas não devem ser somados ou relacionados registro a registro.

## Justificativa

Não é possível reconciliar as duas fontes de forma confiável porque:

* os dados oficiais não possuem CPF disponível;
* os eventos NRT são exclusivamente sintéticos;
* os identificadores são gerados por sistemas diferentes;
* uma triagem não representa necessariamente uma notificação oficial;
* os eventos possuem granularidades e finalidades distintas.

Criar uma correspondência artificial exigiria grande esforço e produziria uma integração sem valor real, construída apenas para a demonstração.

A separação é uma decisão consciente de arquitetura, e não uma falha de implementação. O objetivo do projeto é demonstrar, no mesmo domínio, um fluxo Batch e um fluxo NRT com necessidades diferentes.

## Evolução futura

Uma integração poderia ser avaliada se existissem:

* sistemas hospitalares reais autorizados;
* identificador comum entre triagem e notificação;
* contrato de dados compartilhado;
* regras para evitar duplicidade;
* base legal para o tratamento;
* processo de qualidade e reconciliação específico.

Nesse cenário, os eventos poderiam ser consolidados periodicamente no Data Lake antes de sua incorporação ao modelo analítico.

## Alternativas

* **Criar eventos sintéticos correspondentes aos dados oficiais:** não adotado porque produziria uma reconciliação artificial e pouco representativa.
* **Relacionar registros por data, município, sexo e idade:** não adotado devido ao risco elevado de associações incorretas.
* **Enviar diretamente os eventos NRT para a Gold:** não adotado porque misturaria triagens operacionais com notificações oficiais.
* **Somar os indicadores dos dois fluxos:** não adotado porque possuem significados e granularidades diferentes.
* **Implementar uma consolidação diária sem chave comum:** não adotada devido à complexidade e à ausência de uma regra confiável de correspondência.
