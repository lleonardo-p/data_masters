# Dados de Arboviroses

Este documento descreve o fluxo de dados de arboviroses do BAIP. O contrato
atual foi validado com dados de **dengue** do SINAN/OpenDataSUS e está preparado
para evolução com Zika e Chikungunya.

## Fontes de dados

| Fonte | Uso |
|---|---|
| SINAN/OpenDataSUS | Notificações e investigações de arboviroses |
| API de Localidades do IBGE | Nome do município, UF e região |

O SINAN utiliza código municipal com seis dígitos e o IBGE utiliza sete. A
Silver cria uma chave auxiliar com os seis primeiros dígitos do código IBGE para
realizar o enriquecimento.

## Responsabilidade das camadas

| Camada | Responsabilidade | Formato |
|---|---|---|
| Bronze | Preservar a origem e permitir auditoria e reprocessamento | Parquet/Snappy |
| Silver | Limpar, tipar, padronizar, deduplicar, validar e enriquecer | Parquet/Snappy |
| Gold/DW | Criar fatos, dimensões e métricas para Athena e Power BI | Parquet/Snappy |

## Bronze

A Bronze lê os JSONL da Staging, preserva todas as colunas recebidas e adiciona
somente metadados técnicos. Não traduz códigos nem aplica regras de negócio.

Metadados adicionados:

```text
disease, _source_file, _staging_extract_date, _partition_date,
_bronze_loaded_at, _environment, year, month
```

Principais operações:

- identifica a doença pelo campo técnico `_source`;
- converte JSONL para Parquet com Snappy;
- mantém datas ausentes ou inválidas em partições `unknown`;
- particiona mensalmente por doença e data de notificação.

```text
bronze/opendatasus/arboviroses/
└── disease=<disease>/year=<YYYY>/month=<MM>/
```

## Silver

A Silver possui grão de **uma notificação por registro**. Ela mantém as colunas
necessárias para qualidade, análise e construção da Gold. As demais continuam
disponíveis na Bronze.

| Grupo | Colunas mantidas ou derivadas |
|---|---|
| Linhagem | `record_id`, `record_hash`, `source_system`, `source_reference_year`, `source_offset`, `source_row_number`, `extracted_at`, `source_file`, `bronze_loaded_at`, `silver_loaded_at`, `environment`, `data_quality_status`, `quality_warning_codes` |
| Notificação | `disease_code`, `disease_name`, `notification_year`, `notification_date`, `notification_epidemiological_week`, `symptoms_start_date`, `symptoms_epidemiological_week`, `investigation_date`, `digitization_date`, `closure_date` |
| Residência | códigos SINAN/IBGE, nome do município, código/sigla/nome da UF e código/sigla/nome da região |
| Notificação | códigos SINAN/IBGE e atributos do município, UF e região notificante |
| Infecção | códigos SINAN/IBGE e atributos do município, UF e região provável de infecção, país e unidade de saúde |
| Demografia | `birth_year`, `age_encoded`, `age_unit_code`, `age_unit_name`, `age_value`, `age_years`, códigos e descrições de sexo, gestação, raça e escolaridade |
| Caso | códigos e descrições de classificação, critério de confirmação, evolução, hospitalização e autoctonia; datas de internação e óbito; sorotipo |
| Indicadores | `is_confirmed_case`, `is_discarded_case`, `is_alarm_case`, `is_severe_case`, `is_under_investigation`, `is_hospitalized`, `is_death_by_disease`, `is_death_other_cause`, `is_autochthonous` |

O município de residência (`id_mn_resi`) é a geografia principal dos
indicadores. Município notificante e provável município de infecção permanecem
como contextos distintos.

O campo `nu_idade_n` é codificado: o primeiro dígito representa hora, dia, mês
ou ano, e os demais representam o valor. `age_years` só é preenchida quando a
unidade original é ano.

Tratamentos:

- converte `"nan"`, strings vazias, `"null"` e `"none"` para nulo real;
- renomeia e tipa as colunas;
- enriquece municípios com a referência IBGE;
- mantém o código original e cria sua descrição;
- deduplica pela identidade técnica da paginação;
- valida datas e envia erros críticos para quarentena.

Os mapeamentos atuais de classificação foram validados para Dengue e
Chikungunya. Zika deverá receber seu dicionário específico antes da consolidação
na Gold.

```text
silver/opendatasus/arboviroses/
└── disease_name=<disease>/year=<YYYY>/month=<MM>/
```

### Qualidade e quarentena

São enviados para quarentena registros com doença desconhecida, data de
notificação inválida, município de residência ausente ou não localizado no
IBGE, identidade técnica ausente, inconsistência entre datas ou duplicidade.

Ausência de classificação, critério, evolução ou hospitalização gera alerta,
mas não remove o registro da Silver.

```text
quarantine/opendatasus/arboviroses/silver_cases/
└── primary_error_code=<error>/quarantine_year=<YYYY>/quarantine_month=<MM>/
```

## Gold/DW

A Gold implementa um modelo estrela sem dados de identificação pessoal. A fato
tem grão de **uma linha por notificação Silver**; suas métricas inteiras podem
ser somadas com segurança no Athena e no Power BI.

Dimensões implementadas:

```text
dim_date
dim_disease
dim_location
dim_demographic
dim_clinical
```

Fato:

```text
fact_arbovirus_cases
```

`dim_date` e `dim_location` são dimensões de papéis. Uma mesma linha da fato
possui chaves diferentes para data de notificação, sintomas, investigação,
digitação, internação, encerramento e óbito, além de residência, local
notificante e local provável de infecção.

Métricas planejadas:

```text
notification_count
confirmed_case_count
discarded_case_count
alarm_case_count
severe_case_count
hospitalized_case_count
death_by_disease_count
death_other_cause_count
under_investigation_count
autochthonous_case_count
quality_warning_count
```

`notification_count` não representa apenas casos confirmados, pois também pode
incluir notificações em investigação ou posteriormente descartadas.

A Gold recebe registros Silver com status `valid` e `warning`. Registros de
quarentena não são lidos. Chaves `-1` representam atributos desconhecidos. As
chaves das dimensões são determinísticas, permitindo reprocessamentos sem
alterar relacionamentos.

```text
gold/opendatasus/arboviroses/
├── dim_date/
├── dim_location/
├── dim_disease/
├── dim_demographic/
├── dim_clinical/
└── fact_arbovirus_cases/notification_year=<YYYY>/notification_month=<MM>/
```

Após o job, o crawler cadastra as tabelas no banco Gold do Glue Catalog para
consulta pelo Athena.

## Paths de referência

```text
reference/ibge/municipalities/municipios_ufs_ibge.json
bronze/opendatasus/arboviroses/
silver/opendatasus/arboviroses/
gold/opendatasus/arboviroses/
quarantine/opendatasus/arboviroses/silver_cases/
```

## Documentação utilizada

- [Portal de Dados Abertos do SUS — Arboviroses](https://dadosabertos.saude.gov.br/dataset?groups=arboviroses)
- [Sinan/Dengue](https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue)
- [Sinan/Febre de Chikungunya](https://dadosabertos.saude.gov.br/dataset/arboviroses-febre-de-chikungunya)
- [Dicionário de Dados — Dengue e Chikungunya](https://portalsinan.saude.gov.br/images/documentos/Agravos/Dengue/DIC_DADOS_ONLINE.pdf)
- [Ficha de Investigação — Dengue e Chikungunya](https://portalsinan.saude.gov.br/images/documentos/Agravos/Dengue/Ficha_DENGCHIK_FINAL.pdf)
- [Dicionário de Notificação Individual do SINAN](https://portalsinan.saude.gov.br/images/documentos/Agravos/NINDIV/DIC_DADOS_NET_Not_Individual_rev.pdf)
- [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades)
- [Endpoint de municípios do IBGE](https://servicodados.ibge.gov.br/api/v1/localidades/municipios)
