# ADR-015: Particionamento, Layout e Formato de Arquivos

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O desempenho e o custo das consultas no Data Lake dependem diretamente do formato dos arquivos, tamanho dos objetos, particionamento e organização dos prefixos no Amazon S3.

O BAIP precisa suportar reprocessamento, consultas analíticas por período, rastreabilidade por fonte e organização dos dados por camada do Data Lake.

Como o projeto está em fase de MVP, o particionamento deve ser simples, previsível e alinhado aos principais padrões de consulta, evitando excesso de partições e complexidade operacional desnecessária.

## Decisão

A arquitetura adotará:

- **JSON ou formato original** na camada Bronze, quando necessário para preservar auditoria e rastreabilidade da fonte;
- **Parquet** nas camadas Silver, Gold e DW;
- **particionamento mensal** como padrão para tabelas analíticas e tratadas;
- compactação periódica para evitar excesso de pequenos arquivos;
- nomes de pastas padronizados por camada, domínio, fonte e período;
- particionamento orientado pelos padrões de consulta, e não apenas pela estrutura original da fonte.

O particionamento mensal será utilizado para reduzir a quantidade de partições e manter boa eficiência em consultas por período.

O padrão sugerido para partições será:

```text
year=YYYY/month=MM
```

Exemplo:

```text
s3://baip-data-lake/silver/health/dengue/year=2026/month=07/
s3://baip-data-lake/gold/indicators/arbovirus_cases/year=2026/month=07/
```

Campos como domínio, fonte e camada poderão ser usados na organização dos prefixos do S3, mas não necessariamente como partições formais das tabelas.

Não será adotado particionamento diário no MVP, pois o volume inicial não justifica esse nível de granularidade e poderia gerar excesso de partições e pequenos arquivos.

## Justificativa

O formato Parquet reduz o volume de dados lidos em consultas analíticas, melhora a performance e reduz custos no Athena por ser colunar e eficiente para filtros e agregações.

O particionamento mensal atende ao padrão esperado de consulta do projeto, que tende a analisar séries históricas, indicadores por mês, evolução epidemiológica e recortes temporais agregados.

Essa estratégia simplifica a manutenção do Data Lake, reduz a quantidade de partições no Glue Data Catalog e evita a criação excessiva de diretórios e metadados.

A compactação periódica é necessária para manter arquivos em tamanhos mais adequados para leitura analítica, evitando degradação de performance causada por muitos arquivos pequenos.

## Alternativas consideradas

- **CSV em todas as camadas:** simples para leitura manual, mas ineficiente para analytics, com maior custo de leitura e menor performance em consultas.
- **JSON em todas as camadas:** flexível para ingestão e auditoria, mas menos eficiente para consultas analíticas, principalmente em grandes volumes.
- **Particionamento diário:** oferece maior granularidade, mas pode gerar excesso de partições e aumentar a complexidade operacional no MVP.
- **Particionar por muitos campos:** pode parecer vantajoso para filtros específicos, mas aumenta a quantidade de partições, dificulta manutenção e pode prejudicar performance se mal utilizado.
- **Sem particionamento:** simplifica a escrita dos dados, mas aumenta o volume escaneado nas consultas e pode elevar custo e latência no Athena.

## Consequências

### Positivas

- Melhor performance em consultas analíticas por período.
- Redução de custo no Athena por menor volume de dados escaneados.
- Organização clara por camada, domínio, fonte e período.
- Menor quantidade de partições em comparação com particionamento diário.
- Melhor suporte a reprocessamento mensal.
- Maior simplicidade operacional no MVP.

### Negativas / Trade-offs

- Consultas muito específicas por dia podem escanear o mês inteiro.
- Reprocessamentos pontuais podem exigir sobrescrita ou reprocessamento da partição mensal.
- Pode ser necessário evoluir o particionamento se o volume crescer significativamente.
- Exige rotina de compactação para evitar pequenos arquivos.
- Particionamento incorreto ou desalinhado com os filtros das consultas pode reduzir os ganhos de performance.

## Critérios de evolução

Esta decisão deve ser revisada se:

- o volume de dados crescer significativamente;
- consultas por dia se tornarem muito frequentes;
- o custo das consultas no Athena aumentar por excesso de dados escaneados;
- houver necessidade de reprocessamentos mais granulares;
- surgirem muitos dados late arriving;
- forem necessários updates, deletes ou time travel frequentes;
- houver necessidade de formato transacional no Data Lake;
- a arquitetura evoluir para Apache Iceberg, Apache Hudi ou Delta Lake.

## Referências

- Apache Parquet
- Amazon Athena Partitioning
- AWS Glue Data Catalog
- S3 Data Lake Best Practices
