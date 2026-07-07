# Arquitetura Técnica

O projeto consiste em dois fluxos de dados: **batch** e **NRT**. O fluxo batch será executado a cada 1 dia, com possibilidade de **backfill** para reprocessamento histórico. Os dados serão organizados em uma arquitetura medalhão, com zonas **Staging**, **Bronze**, **Silver** e **Gold/DW**. A área de Staging armazenará dados brutos temporários e terá política de deleção/retenção. As camadas analíticas serão catalogadas no **AWS Glue Data Catalog** e consultadas via **Amazon Athena** para consumo no **Power BI**.

## Fluxo Batch

O fluxo batch é responsável por extrair, armazenar, transformar e disponibilizar os dados para análise. A execução é agendada pelo **Amazon EventBridge Scheduler** e orquestrada pelo **AWS Step Functions**, garantindo controle de dependências, retries, falhas e status da execução.

### Etapa de Extração Bruta

A etapa de extração bruta inicia com o agendamento automático do pipeline pelo **EventBridge Scheduler**. Em seguida, o **AWS Step Functions** orquestra a execução da **Raw API Extractor Lambda**, responsável por consultar APIs externas, como OpenDataSUS e Open-Meteo Archive API.

A Lambda busca os dados nas APIs, mantém os registros no formato original e grava os arquivos na **Raw Staging Area** no Amazon S3. Essa área é temporária, organizada por fonte, data e execução, e possui política de retenção/deleção via **S3 Lifecycle Policy**. Logs, métricas e erros da orquestração e da Lambda são centralizados no **Amazon CloudWatch Logs**.

[![System Context](c4/c3_raw_data_extraction_flow.drawio.svg)]

### Camada Silver
