# ADR-014: Consumo Analítico com Power BI e Athena

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP precisa disponibilizar indicadores em dashboards para análise de arboviroses, clima, infraestrutura de saúde e eventos near real-time consolidados.

O consumo deve ocorrer sobre dados tratados e confiáveis, evitando acesso direto às camadas brutas.

## Decisão

O consumo analítico será feito por **Power BI** consultando datasets da camada **Gold/DW**, preferencialmente via **Amazon Athena**.

A exposição para BI deve utilizar tabelas ou views específicas, com:

- dados agregados;
- ausência de PII;
- regras de negócio documentadas;
- particionamento adequado;
- controle de custo via Athena Workgroups.

## Justificativa

Power BI é uma ferramenta acessível para apresentação e Athena permite consulta SQL serverless sobre dados no S3.

A combinação atende ao MVP com baixo custo e sem necessidade inicial de um Data Warehouse dedicado.

## Alternativas consideradas

- **Amazon QuickSight:** integração nativa AWS, mas Power BI pode ser mais familiar e valorizado no portfólio.
- **Amazon Redshift:** melhor para performance previsível em alto volume, mas adiciona custo e operação.
- **Dashboard direto no DynamoDB:** inadequado para análise histórica e consultas analíticas amplas.

## Consequências

### Positivas

- Baixo custo inicial.
- Consumo SQL sobre o Data Lake.
- Boa aderência a dashboards executivos e analíticos.
- Evita duplicação inicial em um DW dedicado.

### Negativas

- Athena cobra por dados escaneados.
- Performance depende de particionamento e formato dos arquivos.
- Power BI pode exigir estratégias de import/cache para melhor experiência.

## Critérios de evolução

Revisar esta decisão se:

- dashboards exigirem baixa latência e alta concorrência;
- o custo de Athena crescer muito;
- consultas ficarem lentas mesmo com otimização;
- for necessário um serving layer analítico dedicado.

## Referências

- Amazon Athena
- Power BI
- Athena Workgroups
