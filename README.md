# 🦟 Arbovirus Intelligence Platform

## Sobre o projeto

O **Arbovirus Intelligence Platform** é um projeto de Engenharia de Dados desenvolvido para construir uma plataforma analítica capaz de integrar diferentes fontes de dados relacionadas às arboviroses no Brasil.

O objetivo é consolidar dados históricos e incrementais de casos de **Dengue**, **Zika** e **Chikungunya**, enriquecendo essas informações com variáveis climáticas, eventos ambientais e indicadores de infraestrutura de saúde. A plataforma permitirá análises históricas, geração de indicadores e suporte à tomada de decisão baseada em dados.

Além da plataforma analítica, o projeto contempla um cenário de dados simulados de um ambiente hospitalar para demonstrar práticas de anonimização de dados sensíveis (PII), governança de dados e processamento em tempo quase real.

---

# Objetivos

* Construir uma plataforma completa de Engenharia de Dados.
* Integrar diferentes fontes públicas de dados.
* Consolidar dados históricos e incrementais.
* Implementar um pipeline de processamento utilizando arquitetura em camadas.
* Disponibilizar dados analíticos para dashboards e indicadores de negócio.
* Demonstrar boas práticas de governança, observabilidade, qualidade e segurança de dados.
* Simular um ambiente hospitalar para tratamento de dados sensíveis em conformidade com a LGPD.

---

# Fontes de Dados

## Saúde

* OpenDataSUS

  * Dengue
  * Zika
  * Chikungunya
  * PMMB (Programa Mais Médicos para o Brasil)
  * Unidades Básicas de Saúde (UBS)
  * Hospitais e Leitos

## Clima

* Open-Meteo

## Eventos Ambientais

* NASA EONET

---

# Fluxo 1 — Plataforma Analítica

O primeiro fluxo é responsável pela construção da plataforma analítica utilizando dados públicos.

## Extração

Nesta etapa são realizadas:

* Extração dos dados através das APIs públicas;
* Armazenamento dos dados brutos na camada **Bronze**;
* Coleta de métricas de execução, como:

  * tempo de processamento;
  * quantidade de registros;
  * sucesso ou falha da execução.

## Data Preparation

A camada **Silver** é responsável pelo tratamento e padronização dos dados.

As principais atividades incluem:

* Seleção das colunas relevantes;
* Conversão de tipos de dados;
* Tratamento de valores nulos;
* Padronização dos dados;
* Regras de qualidade;
* Enriquecimento das informações;
* Geração de métricas de processamento.

## Data Warehouse

A partir da camada **Silver** será construída uma camada analítica contendo tabelas fato e dimensão, seguindo modelagem dimensional (Star Schema).

Esta camada será responsável por disponibilizar os dados para consumo pelos dashboards e indicadores de negócio.

---

# Fluxo 2 — Dados Simulados

Além dos dados públicos, o projeto contará com uma base simulada representando um ambiente hospitalar.

Essa base armazenará informações fictícias de pacientes contendo sintomas e demais informações necessárias para demonstrar um fluxo completo de processamento de dados sensíveis.

O pipeline seguirá as mesmas etapas da plataforma analítica:

* Extração da base operacional;
* Camada Bronze;
* Tratamento dos dados na camada Silver;
* Anonimização e mascaramento de dados (PII);
* Disponibilização dos dados tratados na camada Gold.

Esse fluxo será utilizado para demonstrar práticas relacionadas à **LGPD**, segurança e governança de dados.

---

# Evoluções Futuras

Como evolução da plataforma, estão previstas as seguintes funcionalidades:

* Processamento de eventos em tempo quase real;
* Atualização automática de indicadores epidemiológicos;
* API para disponibilização de resultados;
* Modelo de Machine Learning para classificação probabilística de Dengue, Zika e Chikungunya a partir dos sintomas informados;
* Simulação de integração com sistemas hospitalares.

---

# Escopo do Projeto

Ao final do projeto, espera-se demonstrar uma solução completa contemplando:

* Extração de dados;
* Ingestão de dados;
* Processamento Batch;
* Processamento em Tempo Real (evolução);
* Data Lake;
* Data Warehouse;
* Modelagem Dimensional;
* Observabilidade;
* Qualidade de Dados;
* Segurança;
* Governança;
* Mascaramento e Anonimização de Dados;
* Geração de Dashboards Analíticos;
* Disponibilização de APIs para consumo dos dados.
