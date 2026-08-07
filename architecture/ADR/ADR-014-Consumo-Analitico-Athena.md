# ADR-014: Consumo Analítico com Amazon Athena

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

A camada Gold precisa disponibilizar os dados históricos para consultas epidemiológicas sem exigir um banco de dados analítico dedicado.

O consumo deve permitir consultas SQL sobre fatos, dimensões e indicadores agregados, mantendo baixo esforço operacional.

## Decisão

Disponibilizar os dados analíticos do fluxo Batch exclusivamente pelo Amazon Athena.

O acesso ocorre por meio de:

* tabelas da Gold registradas no Glue Data Catalog;
* views analíticas com regras de negócio padronizadas;
* workgroup exclusivo do projeto;
* permissões controladas por AWS IAM;
* resultados armazenados em um bucket S3 específico.

Não será disponibilizado acesso direto aos arquivos da Gold, banco relacional, API analítica ou ferramenta externa de BI.

O fluxo NRT permanece separado e disponibiliza seus indicadores por API.

## Justificativa

O Athena consulta diretamente os arquivos Parquet no Amazon S3 e não exige provisionamento ou administração de servidores.

A integração com Glue Data Catalog permite utilizar SQL sobre as tabelas da Gold. As views simplificam os relacionamentos do Star Schema e centralizam as métricas utilizadas nas análises.

O workgroup permite controlar resultados, métricas e limite de dados examinados por consulta.

## Limitação atual

O projeto não possui dashboard de BI conectado à camada Gold. As consultas e evidências analíticas são executadas diretamente no Athena.

Essa limitação é aceitável porque o objetivo principal é demonstrar a disponibilização de dados confiáveis e consultáveis, e não desenvolver uma aplicação de visualização.

## Alternativas

* **Amazon Redshift:** não adotado porque exigiria uma camada adicional de carga e aumentaria o custo para o volume atual.
* **Banco de dados relacional:** não adotado porque não é necessário para consultas analíticas sobre arquivos Parquet.
* **API analítica sobre a Gold:** não adotada porque adicionaria desenvolvimento, manutenção e controle de capacidade.
* **Power BI ou Amazon QuickSight:** não adotados porque a construção de dashboards não faz parte do escopo principal.
* **Acesso direto ao Amazon S3:** não adotado porque contornaria os contratos de consumo definidos pelas tabelas e views do Athena.
