# Caso 1 — Pipeline batch de dengue

> Documento de contexto de negócio. Para arquitetura, componentes e operação,
> consulte a [visão ponta a ponta](../batch-dengue/README.md).

## Objetivo

Demonstrar o ciclo completo de um dado recebido por arquivo: entrada governada,
preservação, padronização, qualidade, enriquecimento, modelagem dimensional,
catálogo, consulta e consumo.

## Cenário de negócio da subida manual

O case simula um parceiro ou órgão externo que entrega extratos periódicos em
arquivo, situação comum quando não existe API estável, a integração ainda não
foi contratada ou a publicação oficial ocorre em lotes fechados. Um data steward
ou ingestion operator autorizado é responsável por:

1. confirmar fonte, período de referência e nome esperado;
2. verificar tamanho e checksum disponibilizado ou calculado;
3. enviar o objeto ao prefixo de Staging autorizado;
4. registrar o recebimento e o identificador do lote;
5. iniciar ou autorizar o processamento.

No MVP, essas verificações são um procedimento documentado. Em produção, o
mesmo contrato poderia ser atendido por S3 Transfer Family, DataSync, URL
pré-assinada ou integração do sistema fornecedor. A forma de transporte muda;
o contrato de recebimento permanece.

## Fonte

- SINAN/OpenDataSUS — arquivos anuais de dengue `DENGBRYY.csv`;
- dicionário e ficha de investigação do SINAN;
- referência de municípios da API de Localidades do IBGE.

O código `A90` identifica dengue no contrato atual. Os arquivos analisados
possuem 121 colunas e schema compatível entre 2024, 2025 e 2026.

## Fluxo implementado

### 1. Staging

```text
s3://<lake>/staging/opendatasus/dengue/reference_year=<YYYY>/DENGBRYY.csv
```

A Staging preserva o arquivo entregue. Ela desacopla o recebimento do
processamento e oferece uma janela curta para retry e comprovação do lote.

Controles recomendados para o recebimento:

- acesso de escrita restrito ao prefixo;
- criptografia e bloqueio de acesso público;
- checksum do S3 ou checksum fornecido pelo produtor;
- metadados `source`, `reference_year`, `received_at` e `batch_id`;
- regra que rejeita sobrescrita acidental do mesmo lote;
- lifecycle após a janela de retenção aprovada.

### 2. Bronze

Job: `baip-dev-bronze-ingestion`.

O job lê CSV com schema explícito e modo `FAILFAST`, normaliza nomes, adiciona
metadados e converte os dados para Parquet/Snappy. Não traduz os códigos de
negócio.

Partições atuais:

```text
bronze/opendatasus/dengue/
└── disease=dengue/
    └── reference_year=<YYYY>/
        └── notification_year=<YYYY>/notification_month=<MM>/
```

`reference_year` identifica o arquivo anual recebido; `notification_year` e
`notification_month` descrevem o evento notificado. A diferença é preservada e
pode gerar warning na Silver, sem alterar o valor da fonte.

### 3. Silver e quarentena

Job: `baip-dev-silver-dengue-cases`.

A Silver possui grão de uma notificação por registro técnico. Ela:

- converte marcadores textuais de ausência em nulos reais;
- tipa datas, códigos, números e indicadores;
- traduz domínios do dicionário de dengue;
- decodifica idade e deriva faixa etária;
- enriquece os três papéis geográficos com o IBGE: residência, notificação e
  provável infecção;
- calcula `record_hash` sobre o conteúdo de origem e `record_id` determinístico;
- identifica duplicatas exatas;
- separa `valid`, `warning` e `quarantined`.

O hash resolve uma limitação real: a fonte não publica uma chave estável
preenchida para todos os registros. Ele permite identificar conteúdo idêntico e
reprocessar de forma determinística. Não representa criptografia, assinatura ou
anonimização.

Erros como doença desconhecida, data crítica inválida, município de residência
ausente/não localizado, identidade técnica incompleta, duplicidade e cronologia
inconsistente seguem para quarentena. Ausência de campos analíticos não críticos
pode gerar warning e permanecer na Silver.

```text
silver/opendatasus/dengue/cases/
quarantine/opendatasus/dengue/silver_cases/
```

A quarentena evita contaminar a Gold sem descartar silenciosamente o registro.
Ela preserva erro, fonte e partição de referência para investigação e
reprocessamento futuro.

### 4. Gold/DW

Job: `baip-dev-gold-dengue-star-schema`.

A fato `fact_dengue_cases` possui uma linha por `record_id` Silver válido ou com
warning. `notification_count=1` é uma medida aditiva; as demais medidas 0/1
permitem agregação segura por dimensões.

Dimensões:

- `dim_date`, com múltiplos papéis de data na fato;
- `dim_location`, com papéis de residência, notificação e infecção;
- `dim_disease`;
- `dim_demographic`;
- `dim_clinical`.

Chaves `-1` representam desconhecido. Chaves derivadas de atributos são
determinísticas, reduzindo mudanças de relacionamento em reprocessamentos.

### 5. Catálogo e Athena

O crawler `baip-dev-gold-dengue` registra seis tabelas no database
`baip_dev_gold`, com prefixo `dengue_`. Views controlam a camada semântica de
consumo por município, UF, faixa etária e classificação.

O Athena Workgroup limita cada consulta a 1 GiB escaneado no ambiente dev e
mantém os resultados em bucket separado.

## Controles de reconciliação

O job de reconciliação implementado registra por execução:

```text
bronze_rows
silver_valid_rows
silver_warning_rows
quarantine_rows
gold_rows
duplicate_rows
batch_id
```

Relação principal esperada:

```text
bronze_rows = silver_valid_rows + silver_warning_rows + quarantine_rows
gold_rows = silver_valid_rows + silver_warning_rows
```

Também verifica lote, grão, chaves dimensionais, integridade referencial e
medidas binárias. Diferenças são materializadas no manifesto e interrompem o
fluxo antes do crawler. Checksum da fonte e IDs individuais dos jobs são
extensões recomendadas para o pacote de evidências.

## Escalabilidade

Primeiro, habilitar Glue Auto Scaling, medir skew, shuffle, tempo e DPU-seconds,
e ajustar particionamento e tamanho de arquivos. Arquivos pequenos devem ser
compactados porque aumentam planejamento e requisições no Athena.

EMR passa a ser alternativa quando houver necessidade de controle de runtime,
bibliotecas, clusters persistentes, múltiplos workloads Spark ou economia
comprovada em execução contínua. O aumento de volume, isoladamente, não obriga a
troca: Glue também executa Spark distribuído.

O S3 Standard já distribui dados entre múltiplas Availability Zones na região.
Multi-Region exige replicar dados, catálogo, código, chaves e orquestração, além
de decidir consistência, RTO, RPO e residência. Não é uma opção gratuita de
configuração.

## Evidência atual

- jobs Bronze, Silver e Gold executados na AWS;
- arquivos Parquet nas camadas;
- quarentena produzida;
- Step Functions executada de ponta a ponta;
- manifesto de reconciliação com todos os checks aprovados;
- crawler concluído;
- seis tabelas e cinco views no Athena;
- cinco queries automatizadas de aceitação aprovadas no Athena.

As contagens sanitizadas estão em
[Execução validada](../batch-dengue/validated-run.md).

## Evoluções independentes

- criar testes de schema e regras críticas;
- adicionar validações estáticas ao CI;
- testar a entrega do alerta SNS em um destino configurado;
- conectar um dashboard às views sem alterar o pipeline batch.
