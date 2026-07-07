# ADR-015: Particionamento, Layout e Formato de Arquivos

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O desempenho e o custo das consultas no Data Lake dependem diretamente do formato dos arquivos, tamanho dos objetos, particionamento e organização dos prefixos no S3.

O BAIP precisa suportar reprocessamento, consulta por período, domínio, fonte e localização geográfica.

## Decisão

A arquitetura usará:

- **JSON ou formato original** na Bronze quando necessário para auditoria;
- **Parquet** nas camadas Silver, Gold e DW;
- particionamento por data e, quando fizer sentido, por domínio/fonte/região;
- compactação periódica para evitar pequenos arquivos;
- nomes de pastas padronizados por camada, domínio, fonte e data.

O particionamento deve ser guiado pelos padrões de consulta, não apenas pela estrutura da fonte.

## Justificativa

Parquet reduz custo de leitura em consultas analíticas e melhora performance. Particionamento bem definido reduz dados escaneados e organiza o Data Lake.

A compactação é necessária para evitar degradação causada por muitos arquivos pequenos.

## Alternativas consideradas

- **CSV em todas as camadas:** simples, mas ineficiente para analytics.
- **JSON em todas as camadas:** flexível, mas caro e menos performático para consultas.
- **Particionar por muitos campos:** pode gerar excesso de partições e piorar manutenção.
- **Sem particionamento:** simplifica escrita, mas aumenta custo e latência de leitura.

## Consequências

### Positivas

- Melhor performance analítica.
- Redução de custo no Athena.
- Organização clara por camada e domínio.
- Melhor suporte a reprocessamento.

### Negativas

- Exige manutenção de layout e compactação.
- Particionamento incorreto pode prejudicar consultas.
- Pequenos arquivos podem surgir no near real-time.

## Critérios de evolução

Revisar esta decisão se:

- o volume de dados crescer significativamente;
- forem necessários updates/deletes frequentes;
- late arriving data se tornar comum;
- houver necessidade de tabela transacional no Data Lake.

## Referências

- Apache Parquet
- Amazon Athena Partitioning
- S3 Data Lake Best Practices
