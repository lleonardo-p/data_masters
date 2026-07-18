# Contrato técnico — Dengue

## Identificação

| Campo | Valor |
|---|---|
| Domínio | Saúde pública / arboviroses |
| Dataset | Notificações de dengue |
| Agravo | `A90` |
| Fonte | SINAN/OpenDataSUS |
| Grão Silver | Uma notificação por registro técnico |
| Responsável no case | Engenharia de Dados BAIP |
| Classificação | Dado público de saúde; sem PII direta publicada no produto Gold |

## Arquivos validados

| Arquivo | Ano de referência | Registros observados | Colunas |
|---|---:|---:|---:|
| `DENGBR24.csv` | 2024 | 6.564.924 | 121 |
| `DENGBR25.csv` | 2025 | 1.644.938 | 121 |
| `DENGBR26.csv` | 2026 | 407.750 | 121 |

Os três arquivos analisados apresentaram os mesmos nomes e ordem de colunas.
Essa evidência não elimina a necessidade de validar o schema em novas entregas.

## Fontes complementares

| Fonte | Uso |
|---|---|
| Dicionário SINAN Dengue/Chikungunya | Tipos, códigos e domínios |
| Ficha de investigação SINAN | Interpretação de campos clínicos e epidemiológicos |
| API de Localidades do IBGE | Município, UF e região |

O SINAN usa código municipal de seis dígitos em campos do dataset; a referência
IBGE possui sete. O job cria a chave auxiliar com os seis primeiros dígitos do
código IBGE para realizar o enriquecimento e preserva ambos os valores.

## Staging

Formato recebido: CSV UTF-8 com header.

```text
staging/opendatasus/dengue/reference_year=<YYYY>/DENGBRYY.csv
```

`reference_year` representa a edição anual do arquivo entregue. Não deve ser
inferido apenas pela data de notificação.

## Bronze

A Bronze mantém as 121 colunas da fonte como string e adiciona:

```text
reference_year
notification_year
notification_month
disease
_batch_id
_source_file
_source_system
_source_format
_notification_date
_bronze_loaded_at
_environment
```

O schema é explícito e a leitura usa `FAILFAST`. A conversão para
Parquet/Snappy melhora leitura distribuída e consumo pelas etapas seguintes.

Partições:

```text
disease/reference_year/notification_year/notification_month
```

## Silver

### Linhagem e identidade

```text
record_id
record_hash
source_batch_id
source_system
source_reference_year
source_file
bronze_loaded_at
silver_loaded_at
environment
data_quality_status
quality_warning_codes
```

`record_hash` é SHA-256 determinístico sobre as colunas de origem normalizadas
para identidade. `record_id` combina sistema, ano de referência e hash. Como a
fonte não fornece uma chave estável completa, apenas duplicatas exatas das 121
colunas recebem a mesma identidade.

`source_batch_id` recebe o nome único da execução da Step Functions. Ele
permite reconciliar Bronze, Silver, quarentena e Gold, mas não participa do
hash ou do `record_id`; portanto, a identidade do registro permanece estável
entre reprocessamentos.

### Datas

```text
notification_date
symptoms_start_date
investigation_date
digitization_date
hospitalization_date
closure_date
death_date
notification_epidemiological_week
symptoms_epidemiological_week
```

### Geografia

Três papéis são preservados separadamente:

- residência, geografia principal dos indicadores;
- local de notificação;
- local provável da infecção.

Cada papel pode conter código SINAN, código e nome IBGE, UF e região.

### Demografia

```text
birth_year
age_encoded
age_unit_code
age_unit_name
age_value
age_years
age_group_name
sex_code
sex_name
pregnancy_code
pregnancy_name
race_code
race_name
education_code
education_name
```

`nu_idade_n` codifica unidade no primeiro dígito e valor nos demais. A Silver
preserva a forma original e cria atributos derivados.

### Caso e medidas derivadas

```text
classification_code/name
confirmation_criterion_code/name
case_outcome_code/name
hospitalization_code/name
autochthonous_code/name
serotype_code
is_confirmed_case
is_discarded_case
is_alarm_case
is_severe_case
is_under_investigation
is_hospitalized
is_death_by_disease
is_death_other_cause
is_autochthonous
```

## Qualidade

### Quarentena

Erros críticos implementados:

- doença desconhecida;
- data de notificação ausente, futura ou implausível;
- município de residência ausente ou não localizado no IBGE;
- identidade de origem incompleta;
- registro pertencente a outro `batch_id`;
- sintomas após notificação;
- investigação antes da notificação;
- encerramento antes da investigação;
- óbito antes dos sintomas;
- datas críticas implausíveis;
- ano declarado diferente da data de notificação;
- duplicata exata.

Inconsistências cronológicas permanecem bloqueantes por decisão do projeto e
seguem para quarentena.

### Warning

- classificação ausente ou não mapeada;
- critério de confirmação ausente;
- evolução ausente;
- hospitalização desconhecida;
- município de notificação ou infecção não localizado;
- unidade de idade inválida;
- ano do arquivo diferente do ano da notificação.

Warnings permanecem na Silver e podem chegar à Gold acompanhados de flag.

## Gold

Grão: uma linha na `fact_dengue_cases` para cada `record_id` Silver válido ou
com warning.

Medidas:

```text
notification_count
confirmed_case_count
discarded_case_count
alarm_case_count
severe_case_count
under_investigation_count
hospitalized_case_count
death_by_disease_count
death_other_cause_count
autochthonous_case_count
quality_warning_count
```

Dimensões: data, localização, doença, demografia e atributos clínicos.

## Orquestração e reconciliação

A Step Functions executa Bronze, Silver, Gold, reconciliação e crawler em
sequência. O reconciliador materializa um manifesto JSON por `batch_id` e
bloqueia o catálogo quando contagens, grão, chaves, medidas ou identidade do
lote não fecham. Registros históricos da quarentena são preservados, mas apenas
o lote atual participa da igualdade `Bronze = Silver + quarentena`.

## Paths

```text
staging/opendatasus/dengue/
bronze/opendatasus/dengue/
silver/opendatasus/dengue/cases/
quarantine/opendatasus/dengue/silver_cases/
gold/opendatasus/dengue/
reference/ibge/municipalities/municipios_ufs_ibge.json
```

## Referências

- [Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/)
- [Dataset de dengue](https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue)
- [Dicionário de Dengue e Chikungunya](https://portalsinan.saude.gov.br/images/documentos/Agravos/Dengue/DIC_DADOS_ONLINE.pdf)
- [Ficha de investigação](https://portalsinan.saude.gov.br/images/documentos/Agravos/Dengue/Ficha_DENGCHIK_FINAL.pdf)
- [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades)
