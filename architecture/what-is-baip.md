# O que é o BAIP?

O **BAIP (Brazil Arbovirus Intelligence Platform)** é uma plataforma de Engenharia de Dados desenvolvida para demonstrar a construção de uma solução moderna de dados voltada ao monitoramento, integração e análise de informações relacionadas às arboviroses no Brasil.

O projeto tem como foco principal consolidar dados históricos e incrementais sobre **Dengue**, **Zika** e **Chikungunya**, enriquecendo essas informações com variáveis climáticas, eventos ambientais e indicadores de infraestrutura de saúde. A partir dessa integração, a plataforma permite gerar indicadores epidemiológicos, análises históricas e insumos para tomada de decisão baseada em dados.

Além do fluxo analítico com dados públicos, o BAIP contempla um cenário simulado de integração com Sistemas de Informação hospitalares. Nesse cenário, novos atendimentos de pacientes com suspeita de arboviroses são registrados durante a triagem e publicados como eventos para processamento em tempo quase real. Esse fluxo permite demonstrar práticas de arquitetura orientada a eventos, governança de dados, qualidade, observabilidade e proteção de dados sensíveis em conformidade com a LGPD.

Embora seja um projeto de estudo e portfólio, o BAIP foi desenhado para simular desafios encontrados em ambientes corporativos de dados, contemplando ingestão batch, ingestão near real-time, Data Lake, Lakehouse, Data Warehouse, catálogo de dados, segurança, monitoramento, tratamento de PII e consumo analítico por dashboards.

---

## Objetivos do projeto

O BAIP tem como objetivo demonstrar a construção de uma plataforma completa de Engenharia de Dados, aplicando boas práticas arquiteturais, operacionais e de governança.

Entre os principais objetivos estão:

* Integrar dados públicos de saúde, clima, eventos ambientais e infraestrutura hospitalar.
* Consolidar dados históricos e incrementais sobre Dengue, Zika e Chikungunya.
* Implementar pipelines de ingestão batch para dados públicos.
* Simular um fluxo near real-time para eventos hospitalares de triagem.
* Organizar os dados em uma arquitetura Lakehouse utilizando o padrão Medallion, com camadas Bronze, Silver e Gold.
* Construir uma camada analítica baseada em Data Warehouse e modelagem dimensional.
* Disponibilizar dados tratados para dashboards, indicadores e futuras APIs.
* Implementar regras de qualidade, validação e quarentena de dados.
* Demonstrar práticas de observabilidade, monitoramento e rastreabilidade dos pipelines.
* Aplicar controles de segurança, mascaramento, tokenização e pseudonimização de dados sensíveis.
* Evoluir a plataforma para suportar casos futuros de Machine Learning e análises preditivas.

---

![System Context](c4/context.svg)

---

## Fontes de dados

O projeto utiliza diferentes fontes de dados para compor uma visão integrada das arboviroses no Brasil.

### Saúde

* **OpenDataSUS**

  * Casos de Dengue
  * Casos de Zika
  * Casos de Chikungunya
  * Programa Mais Médicos para o Brasil
  * Unidades Básicas de Saúde
  * Hospitais e leitos

### Clima

* **Open-Meteo**

  * Temperatura
  * Precipitação
  * Umidade
  * Variáveis climáticas relevantes para análise epidemiológica

### Eventos ambientais

* **NASA EONET**

  * Eventos naturais
  * Enchentes
  * Ocorrências ambientais potencialmente relacionadas ao aumento de casos

### Dados simulados

* Sistema hospitalar fictício

  * Pacientes simulados
  * Sintomas informados na triagem
  * Suspeita clínica de arbovirose
  * Eventos de atendimento em tempo quase real

---

## Fluxo 1 — Plataforma analítica batch

O primeiro fluxo do BAIP é responsável pela construção da plataforma analítica baseada em dados públicos.

Esse fluxo realiza a extração, ingestão, tratamento, enriquecimento e consolidação dos dados em uma arquitetura Lakehouse.

### Camada Bronze

A camada **Bronze** armazena os dados brutos extraídos das fontes públicas.

Principais responsabilidades:

* Preservar os dados no formato mais próximo possível da origem.
* Manter histórico das extrações.
* Permitir rastreabilidade e reprocessamento.
* Registrar metadados técnicos da ingestão, como data de execução, origem, status e volume de registros.

### Camada Silver

A camada **Silver** contém dados tratados, padronizados e preparados para análise.

Principais responsabilidades:

* Selecionar colunas relevantes.
* Corrigir tipos de dados.
* Padronizar nomes de campos.
* Tratar valores nulos e inconsistências.
* Aplicar regras de qualidade.
* Remover duplicidades.
* Enriquecer dados com informações climáticas, territoriais e de infraestrutura.
* Separar registros inválidos ou suspeitos em uma área de quarentena.

### Camada Gold e Data Warehouse

A camada **Gold** disponibiliza dados curados, consolidados e otimizados para consumo analítico.

A partir dessa camada, o projeto constrói um **Data Warehouse** com modelagem dimensional, utilizando tabelas fato e dimensão para suportar indicadores epidemiológicos e operacionais.

Exemplos de análises suportadas:

* Casos por município, estado e semana epidemiológica.
* Incidência por 100 mil habitantes.
* Evolução histórica de casos.
* Relação entre casos e variáveis climáticas.
* Comparação entre infraestrutura de saúde e volume de ocorrências.
* Indicadores de atendimento e suspeita clínica no fluxo simulado.

---

## Fluxo 2 — Eventos hospitalares simulados

O segundo fluxo do BAIP simula a integração com um ambiente hospitalar.

Nesse cenário, um sistema fictício de triagem registra atendimentos de pacientes com sintomas compatíveis com arboviroses. Esses atendimentos são publicados como eventos para processamento em tempo quase real.

Esse fluxo tem como objetivo demonstrar:

* Arquitetura orientada a eventos.
* Processamento near real-time.
* Validação de schema contract.
* Idempotência no processamento de eventos.
* Tratamento de falhas com fila de erro.
* Atualização de indicadores recentes.
* Proteção de dados sensíveis de pacientes.

Os dados sensíveis presentes nesse fluxo não devem ser disponibilizados diretamente nas camadas analíticas. Informações como CPF, nome ou identificadores diretos devem ser mascaradas, tokenizadas ou pseudonimizadas antes de qualquer uso analítico.

---

## Governança, segurança e qualidade

O BAIP incorpora práticas de governança e segurança desde o desenho da arquitetura.

Entre os principais controles considerados estão:

* Controle de acesso com princípio de menor privilégio.
* Criptografia dos dados em repouso.
* Separação entre dados brutos, tratados e analíticos.
* Catálogo de dados e metadados técnicos.
* Classificação de dados sensíveis.
* Mascaramento, tokenização e pseudonimização de PII.
* Regras de qualidade por camada.
* Área de quarentena para registros inválidos.
* Logs, métricas e alarmes para monitoramento operacional.
* Políticas de retenção e ciclo de vida dos dados.

Essas práticas permitem aproximar o projeto de um cenário corporativo real, no qual segurança, rastreabilidade, confiabilidade e conformidade são requisitos fundamentais.

---

## Escopo da plataforma

Ao final do projeto, a plataforma deve demonstrar uma solução completa contemplando:

* Extração e ingestão de dados públicos.
* Processamento batch.
* Processamento near real-time simulado.
* Data Lake em camadas.
* Lakehouse com padrão Medallion.
* Data Warehouse com modelagem dimensional.
* Qualidade de dados.
* Governança e catálogo.
* Observabilidade e monitoramento.
* Segurança e tratamento de PII.
* Dashboards analíticos.
* Base para futuras APIs e modelos de Machine Learning.

---

## Evoluções futuras

Como evolução da plataforma, estão previstas as seguintes melhorias:

* Disponibilização de uma API para consulta de indicadores.
* Criação de modelos de Machine Learning para classificação probabilística de Dengue, Zika e Chikungunya com base em sintomas.
* Evolução do processamento near real-time para maior escala.
* Adoção de formatos transacionais no Lakehouse, como Apache Iceberg.
* Expansão da arquitetura para cenários de Multi-AZ, Disaster Recovery e Multi-Region.
* Implementação de controles avançados de governança com catálogo, lineage e gestão de permissões mais granular.