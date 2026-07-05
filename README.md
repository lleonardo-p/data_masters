# 🦟 BAIP — Brazil Arbovirus Intelligence Platform

O **BAIP (Brazil Arbovirus Intelligence Platform)** é um projeto de Engenharia de Dados desenvolvido para demonstrar a construção de uma plataforma moderna de dados voltada ao monitoramento e análise de arboviroses no Brasil.

A solução integra dados públicos de saúde, clima, eventos ambientais e infraestrutura hospitalar, permitindo consolidar informações históricas e incrementais sobre **Dengue**, **Zika** e **Chikungunya**. A plataforma utiliza uma arquitetura Lakehouse em camadas, seguindo o padrão **Medallion Architecture** com Bronze, Silver e Gold, além de uma camada analítica modelada em **Data Warehouse** para consumo por dashboards e indicadores.

Além do fluxo analítico baseado em dados públicos, o projeto também contempla um cenário simulado de integração hospitalar, no qual atendimentos de pacientes com suspeita de arboviroses são publicados como eventos para processamento em tempo quase real. Esse fluxo permite demonstrar práticas de governança, segurança, qualidade de dados, observabilidade e tratamento de dados sensíveis em conformidade com a LGPD.

Embora seja um projeto de estudo e portfólio, o BAIP busca reproduzir desafios reais encontrados em ambientes corporativos de dados, incluindo ingestão batch, ingestão orientada a eventos, Data Lake, Data Warehouse, catálogo de dados, regras de qualidade, mascaramento de PII, monitoramento de pipelines e disponibilização de dados para análise.

## Principais objetivos

* Integrar múltiplas fontes públicas de dados relacionadas a arboviroses no Brasil.
* Construir pipelines de ingestão batch e near real-time.
* Organizar os dados em uma arquitetura Lakehouse com camadas Bronze, Silver e Gold.
* Construir uma camada analítica baseada em modelagem dimensional.
* Disponibilizar indicadores epidemiológicos e operacionais para dashboards.
* Demonstrar boas práticas de governança, segurança, observabilidade e qualidade de dados.
* Simular o tratamento de dados sensíveis de pacientes utilizando mascaramento, tokenização e pseudonimização.
* Preparar a base da plataforma para futuras evoluções com APIs e modelos de Machine Learning.
