# ADR-014: Consumo Analítico com Power BI e Amazon Athena

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa disponibilizar indicadores analíticos para exploração e visualização em dashboards.

A solução deve permitir consultas SQL sobre dados no S3, integração com ferramenta de BI e baixo custo para o MVP.

## Decisão

O consumo analítico será feito com **Power BI** conectado ao **Amazon Athena** sobre tabelas ou views da camada **Gold/DW**.

O Power BI deverá consumir apenas tabelas ou views preparadas para análise, evitando acesso direto às camadas Staging, Bronze e Silver.

As consultas deverão ser otimizadas por formato Parquet, particionamento adequado e uso de views/tabelas específicas para consumo.

Athena Workgroups deverão ser utilizados quando necessário para controle de custo, isolamento e configuração de resultados.

## Justificativa

Athena permite consultar dados no S3 sem provisionar infraestrutura de banco dedicado, reduzindo custo e complexidade no MVP.

Power BI é uma ferramenta conhecida para visualização, exploração e criação de dashboards, com possibilidade de conexão a fontes SQL.

Limitar o consumo à Gold/DW reduz risco de exposição de dados brutos, melhora performance e evita que regras de negócio sejam reimplementadas diretamente no dashboard.

## Alternativas consideradas

- **Amazon QuickSight:** possui integração nativa com AWS, mas Power BI foi priorizado pela familiaridade e facilidade de uso para o projeto.
- **Amazon Redshift:** oferece performance previsível para DW, mas adiciona custo e administração fora do escopo inicial.
- **Consulta direta na Silver:** reduz uma etapa, mas expõe dados ainda não preparados para consumo analítico.
- **Dashboard lendo DynamoDB:** pode atender indicadores operacionais recentes, mas não é adequado para histórico analítico completo.

## Consequências

### Positivas

- Baixo custo inicial.
- Consulta direta em dados no S3.
- Separação entre camada analítica e camada bruta/tratada.
- Boa integração com modelo dimensional Gold/DW.
- Possibilidade de controlar custo por Workgroup.
- Evita provisionamento de Data Warehouse dedicado no MVP.

### Negativas / Trade-offs

- Performance pode variar conforme layout, particionamento e volume escaneado.
- Athena cobra por dados lidos, exigindo otimização de arquivos e consultas.
- Power BI pode exigir estratégia de importação, cache ou atualização agendada.
- Não é ideal para alta concorrência ou dashboards de baixa latência em grande escala.

## Escalabilidade e alternativas

Workgroups por consumidor limitam bytes, isolam resultados e permitem atribuir
custo. O dashboard deve usar import/cache e atualização coerente com a cadência
batch, evitando polling frequente do Athena. Views protegem o contrato, mas
consultas precisam continuar filtrando partições.

Redshift será avaliado para alta concorrência e latência previsível. A API NRT
não deve consultar Athena a cada dois minutos; usa store de serving e mantém a
Gold como visão consolidada.

## Critérios de evolução

Esta decisão deve ser revisada se:

- os dashboards exigirem baixa latência e alta concorrência;
- o custo de consultas Athena crescer acima do previsto;
- houver necessidade de semântica corporativa centralizada;
- o volume de dados exigir Data Warehouse dedicado;
- os indicadores near real-time precisarem ser integrados diretamente ao BI.

## Referências

- Amazon Athena
- Athena Workgroups
- Power BI
- AWS Glue Data Catalog
- Apache Parquet
