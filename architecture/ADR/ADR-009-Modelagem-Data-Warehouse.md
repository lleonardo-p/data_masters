# ADR-009: Modelagem Analítica em Star Schema

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

A camada Gold precisa transformar os registros tratados da Silver em uma estrutura simples para consultas epidemiológicas no Athena.

As análises combinam métricas de notificações, confirmações, hospitalizações, casos graves e óbitos com diferentes perspectivas de data, localização, doença, perfil demográfico e informações clínicas.

## Decisão

Adotar um modelo dimensional Star Schema composto por:

* `fact_dengue_cases`: uma linha por caso de dengue;
* `dim_date`: datas utilizadas durante a evolução do caso;
* `dim_location`: municípios, UFs e demais referências territoriais;
* `dim_disease`: doença e classificação final;
* `dim_demographic`: sexo, idade, faixa etária, raça e escolaridade;
* `dim_clinical`: hospitalização, evolução e demais características clínicas.

A tabela fato armazena chaves para as dimensões e medidas binárias, como notificação, confirmação, hospitalização, gravidade e óbito.

## Justificativa

O Star Schema separa os eventos mensuráveis de seus contextos analíticos e oferece:

* consultas mais simples e legíveis;
* menor quantidade de relacionamentos do que modelos normalizados;
* métricas padronizadas entre diferentes análises;
* reutilização das dimensões;
* integração direta com Athena e ferramentas de BI;
* facilidade para criar agregações por período, território e grupo populacional.

O modelo é adequado ao consumo analítico porque prioriza leitura, agregação e compreensão dos dados, em vez de operações transacionais.

## Alternativas

* **Tabela única desnormalizada:** teria consultas iniciais simples, mas repetiria atributos, aumentaria a dificuldade de manutenção e poderia gerar inconsistência entre classificações.
* **Modelo Snowflake:** reduziria redundâncias nas dimensões, mas adicionaria mais tabelas e relacionamentos sem benefício relevante para o volume e a complexidade atuais.
* **Modelo relacional normalizado:** adequado para sistemas transacionais, mas exigiria mais relacionamentos e consultas complexas para análises agregadas.
* **Data Vault:** ofereceria forte rastreabilidade e flexibilidade para múltiplas fontes, mas aumentaria a complexidade e ainda exigiria a criação de um modelo dimensional para consumo.
* **Views diretamente sobre a Silver:** evitariam a materialização da Gold, mas repetiriam regras de negócio nas consultas e aumentariam o custo e a complexidade do consumo.
