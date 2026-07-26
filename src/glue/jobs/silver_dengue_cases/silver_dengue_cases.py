import logging
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from awsglue.utils import getResolvedOptions
from pyspark import StorageLevel
from pyspark.sql import Column, DataFrame, SparkSession, Window
from pyspark.sql.functions import (
    array,
    array_union,
    broadcast,
    coalesce,
    col,
    concat_ws,
    count,
    current_date,
    current_timestamp,
    date_format,
    element_at,
    filter as array_filter,
    lit,
    lower,
    row_number,
    sha2,
    size,
    substring,
    sum as spark_sum,
    to_date,
    to_timestamp,
    trim,
    upper,
    when,
    year as spark_year,
)


NULL_TEXT_VALUES = ["", "nan", "null", "none"]

CLASSIFICATION_MAPPING = {
    "5": "Descartado",
    "8": "Descartado (código legado)",
    "10": "Dengue",
    "11": "Dengue com sinais de alarme",
    "12": "Dengue grave",
    "13": "Chikungunya",
}

CONFIRMATION_CRITERION_MAPPING = {
    "1": "Laboratorial",
    "2": "Clínico-epidemiológico",
    "3": "Em investigação",
}

CASE_OUTCOME_MAPPING = {
    "1": "Cura",
    "2": "Óbito pelo agravo",
    "3": "Óbito por outras causas",
    "4": "Óbito em investigação",
    "9": "Ignorado",
}

SEX_MAPPING = {
    "M": "Masculino",
    "F": "Feminino",
    "I": "Ignorado",
}

PREGNANCY_MAPPING = {
    "1": "1º trimestre",
    "2": "2º trimestre",
    "3": "3º trimestre",
    "4": "Idade gestacional ignorada",
    "5": "Não",
    "6": "Não se aplica",
    "9": "Ignorado",
}

RACE_MAPPING = {
    "1": "Branca",
    "2": "Preta",
    "3": "Amarela",
    "4": "Parda",
    "5": "Indígena",
    "9": "Ignorado",
}

EDUCATION_MAPPING = {
    "0": "Analfabeto",
    "1": "1ª a 4ª série incompleta do ensino fundamental",
    "2": "4ª série completa do ensino fundamental",
    "3": "5ª a 8ª série incompleta do ensino fundamental",
    "4": "Ensino fundamental completo",
    "5": "Ensino médio incompleto",
    "6": "Ensino médio completo",
    "7": "Educação superior incompleta",
    "8": "Educação superior completa",
    "9": "Ignorado",
    "10": "Não se aplica",
}

AGE_UNIT_MAPPING = {
    "1": "Hora",
    "2": "Dia",
    "3": "Mês",
    "4": "Ano",
}

HOSPITALIZATION_MAPPING = {
    "1": "Sim",
    "2": "Não",
    "9": "Ignorado",
}

AUTOCHTHONOUS_MAPPING = {
    "1": "Sim",
    "2": "Não",
    "3": "Indeterminado",
}


def configure_logger(job_name: str) -> logging.Logger:
    logger = logging.getLogger(job_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        formatter.converter = time.gmtime
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def clean_string(column: Column) -> Column:
    cleaned = trim(column.cast("string"))

    return when(
        cleaned.isNull() | lower(cleaned).isin(*NULL_TEXT_VALUES),
        lit(None).cast("string"),
    ).otherwise(cleaned)


def source_string(df: DataFrame, column_name: str) -> Column:
    if column_name not in df.columns:
        return lit(None).cast("string")

    return clean_string(col(column_name))


def map_code(column_name: str, mapping: dict[str, str]) -> Column:
    expression = when(
        col(column_name).isNull(),
        lit(None).cast("string"),
    )

    for code, description in mapping.items():
        expression = expression.when(
            col(column_name) == lit(code),
            lit(description),
        )

    return expression.otherwise(lit("Não mapeado"))


def location_projection(
    df_ibge: DataFrame,
    prefix: str,
) -> DataFrame:
    return df_ibge.select(
        col("municipality_code_sinan").alias(f"_{prefix}_join_code"),
        col("municipality_code_ibge").alias(
            f"{prefix}_municipality_code_ibge"
        ),
        col("municipality_name").alias(f"{prefix}_municipality_name"),
        col("uf_code").alias(f"{prefix}_uf_code"),
        col("uf_abbreviation").alias(f"{prefix}_uf_abbreviation"),
        col("uf_name").alias(f"{prefix}_uf_name"),
        col("region_code").alias(f"{prefix}_region_code"),
        col("region_abbreviation").alias(
            f"{prefix}_region_abbreviation"
        ),
        col("region_name").alias(f"{prefix}_region_name"),
    )


def parse_bronze_input_path(bronze_input_path: str) -> dict[str, str]:
    normalized_path = bronze_input_path.rstrip("/")
    parsed = urlparse(normalized_path)

    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(
            "BRONZE_INPUT_PATH must be a valid S3 URI."
        )

    match = re.search(
        r"^(?P<base_path>/.+)"
        r"/processing_date=(?P<processing_date>[0-9]{4}-[0-9]{2}-[0-9]{2})"
        r"/granularity=(?P<granularity>day|month)"
        r"/reference_period=(?P<reference_period>[0-9]{4}-(?:[0-9]{2}|[0-9]{2}-[0-9]{2}))$",
        parsed.path,
    )

    if match is None:
        raise ValueError(
            "BRONZE_INPUT_PATH does not follow the expected partition layout."
        )

    metadata = match.groupdict()
    reference_period = metadata["reference_period"]
    granularity = metadata["granularity"]

    if granularity == "month" and len(reference_period) != 7:
        raise ValueError(
            "Monthly input requires reference_period=YYYY-MM."
        )

    if granularity == "day" and len(reference_period) != 10:
        raise ValueError(
            "Daily input requires reference_period=YYYY-MM-DD."
        )

    datetime.strptime(
        metadata["processing_date"],
        "%Y-%m-%d",
    )
    datetime.strptime(
        reference_period,
        "%Y-%m" if granularity == "month" else "%Y-%m-%d",
    )

    base_prefix = metadata["base_path"].lstrip("/")

    return {
        "bucket": parsed.netloc,
        "base_uri": f"s3://{parsed.netloc}/{base_prefix}/",
        "processing_date": metadata["processing_date"],
        "granularity": granularity,
        "reference_period": reference_period,
    }


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "BATCH_ID",
        "ENVIRONMENT",
        "BRONZE_INPUT_PATH",
        "IBGE_REFERENCE_PATH",
        "SILVER_OUTPUT_PATH",
        "QUARANTINE_OUTPUT_PATH",
        "WRITE_MODE",
    ],
)

job_name = args["JOB_NAME"]
batch_id = args["BATCH_ID"]
environment = args["ENVIRONMENT"]
bronze_input_path = args["BRONZE_INPUT_PATH"]
ibge_reference_path = args["IBGE_REFERENCE_PATH"]
silver_output_path = args["SILVER_OUTPUT_PATH"]
quarantine_output_path = args["QUARANTINE_OUTPUT_PATH"]
write_mode = args["WRITE_MODE"].lower()

if write_mode not in {"append", "overwrite"}:
    raise ValueError(
        f"Invalid WRITE_MODE: {write_mode}. Expected append or overwrite."
    )

logger = configure_logger(job_name)
spark = SparkSession.builder.appName(job_name).getOrCreate()
bronze_partition = parse_bronze_input_path(bronze_input_path)

spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.parquet.compression.codec", "snappy")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
spark.conf.set("spark.sql.shuffle.partitions", "48")

logger.info(
    {
        "event": "silver_dengue_cases_started",
        "job_name": job_name,
        "batch_id": batch_id,
        "environment": environment,
        "bronze_input_path": bronze_input_path,
        "processing_date": bronze_partition["processing_date"],
        "granularity": bronze_partition["granularity"],
        "reference_period": bronze_partition["reference_period"],
        "ibge_reference_path": ibge_reference_path,
        "silver_output_path": silver_output_path,
        "quarantine_output_path": quarantine_output_path,
        "write_mode": write_mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

df_bronze = (
    spark.read
    .option("basePath", bronze_partition["base_uri"])
    .parquet(bronze_input_path)
    .withColumn(
        "processing_date",
        lit(bronze_partition["processing_date"]),
    )
    .withColumn(
        "granularity",
        lit(bronze_partition["granularity"]),
    )
    .withColumn(
        "reference_period",
        lit(bronze_partition["reference_period"]),
    )
)

required_bronze_columns = {
    "_batch_id",
    "_bronze_loaded_at",
    "_ingestion_source",
    "_source_extraction_batch_id",
    "_source_file",
    "_source_manifest",
    "_source_system",
    "processing_date",
    "granularity",
    "reference_period",
    "disease",
    "id_agravo",
    "dt_notific",
    "id_mn_resi",
    "reference_year",
}

missing_bronze_columns = sorted(
    required_bronze_columns.difference(df_bronze.columns)
)

if missing_bronze_columns:
    raise ValueError(
        "Missing required Bronze columns: "
        f"{', '.join(missing_bronze_columns)}"
    )

# O arquivo anual nao possui uma chave publica de notificacao confiavel.
# O hash usa as 121 colunas de negocio da fonte e nao inclui metadados de carga
# nem colunas derivadas de particionamento.
hash_source_columns = sorted(
    column_name
    for column_name in df_bronze.columns
    if not column_name.startswith("_")
    and column_name
    not in {
        "disease",
        "reference_year",
        "notification_year",
        "notification_month",
        "processing_date",
        "granularity",
        "reference_period",
    }
)

df_bronze = df_bronze.withColumn(
    "_source_record_hash",
    sha2(
        concat_ws(
            "||",
            *[
                coalesce(col(name).cast("string"), lit("<null>"))
                for name in hash_source_columns
            ],
        ),
        256,
    ),
)

# O arquivo do IBGE é um único array JSON, por isso multiLine=true.
df_ibge_raw = (
    spark.read.option("multiLine", "true").json(ibge_reference_path)
)

required_ibge_columns = {"id", "nome", "microrregiao"}
missing_ibge_columns = sorted(
    required_ibge_columns.difference(df_ibge_raw.columns)
)

if missing_ibge_columns:
    raise ValueError(
        "Missing required IBGE columns: "
        f"{', '.join(missing_ibge_columns)}"
    )

df_ibge = (
    df_ibge_raw.select(
        col("id").cast("string").alias("municipality_code_ibge"),
        substring(col("id").cast("string"), 1, 6).alias(
            "municipality_code_sinan"
        ),
        col("nome").alias("municipality_name"),
        col("microrregiao.mesorregiao.UF.id")
        .cast("string")
        .alias("uf_code"),
        col("microrregiao.mesorregiao.UF.sigla").alias(
            "uf_abbreviation"
        ),
        col("microrregiao.mesorregiao.UF.nome").alias("uf_name"),
        col("microrregiao.mesorregiao.UF.regiao.id")
        .cast("string")
        .alias("region_code"),
        col("microrregiao.mesorregiao.UF.regiao.sigla").alias(
            "region_abbreviation"
        ),
        col("microrregiao.mesorregiao.UF.regiao.nome").alias(
            "region_name"
        ),
    )
    .dropDuplicates(["municipality_code_sinan"])
)

# Seleção e tipagem do contrato Silver. Colunas não usadas pela Gold continuam
# preservadas na Bronze e podem ser adicionadas em versões futuras do contrato.
df_cases = df_bronze.select(
    source_string(df_bronze, "_batch_id").alias("source_batch_id"),
    source_string(df_bronze, "_source_system").alias("source_system"),
    source_string(df_bronze, "_ingestion_source").alias(
        "ingestion_source"
    ),
    source_string(df_bronze, "_source_extraction_batch_id").alias(
        "source_extraction_batch_id"
    ),
    source_string(df_bronze, "_source_manifest").alias(
        "source_manifest"
    ),
    source_string(df_bronze, "processing_date").alias(
        "processing_date"
    ),
    source_string(df_bronze, "granularity").alias("granularity"),
    source_string(df_bronze, "reference_period").alias(
        "reference_period"
    ),
    source_string(df_bronze, "reference_year")
    .cast("int")
    .alias("source_reference_year"),
    source_string(df_bronze, "_source_file").alias("source_file"),
    to_timestamp(source_string(df_bronze, "_bronze_loaded_at")).alias(
        "bronze_loaded_at"
    ),
    source_string(df_bronze, "_source_record_hash").alias("record_hash"),
    lower(source_string(df_bronze, "disease")).alias("disease_name"),
    upper(source_string(df_bronze, "id_agravo")).alias("disease_code"),
    source_string(df_bronze, "nu_ano")
    .cast("int")
    .alias("notification_year"),
    to_date(source_string(df_bronze, "dt_notific")).alias(
        "notification_date"
    ),
    source_string(df_bronze, "sem_not")
    .cast("int")
    .alias("notification_epidemiological_week"),
    to_date(source_string(df_bronze, "dt_sin_pri")).alias(
        "symptoms_start_date"
    ),
    source_string(df_bronze, "sem_pri")
    .cast("int")
    .alias("symptoms_epidemiological_week"),
    to_date(source_string(df_bronze, "dt_invest")).alias(
        "investigation_date"
    ),
    to_date(source_string(df_bronze, "dt_digita")).alias(
        "digitization_date"
    ),
    to_date(source_string(df_bronze, "dt_encerra")).alias(
        "closure_date"
    ),
    source_string(df_bronze, "id_mn_resi").alias(
        "residence_municipality_code_sinan"
    ),
    source_string(df_bronze, "id_municip").alias(
        "notification_municipality_code_sinan"
    ),
    source_string(df_bronze, "comuninf").alias(
        "infection_municipality_code_sinan"
    ),
    source_string(df_bronze, "sg_uf").alias(
        "residence_uf_code_source"
    ),
    source_string(df_bronze, "sg_uf_not").alias(
        "notification_uf_code_source"
    ),
    source_string(df_bronze, "coufinf").alias(
        "infection_uf_code_source"
    ),
    source_string(df_bronze, "copaisinf").alias(
        "infection_country_code"
    ),
    source_string(df_bronze, "id_unidade").alias("health_unit_code"),
    source_string(df_bronze, "ano_nasc").cast("int").alias("birth_year"),
    source_string(df_bronze, "nu_idade_n").alias("age_encoded"),
    upper(source_string(df_bronze, "cs_sexo")).alias("sex_code"),
    source_string(df_bronze, "cs_gestant").alias("pregnancy_code"),
    source_string(df_bronze, "cs_raca").alias("race_code"),
    source_string(df_bronze, "cs_escol_n").alias("education_code"),
    source_string(df_bronze, "classi_fin").alias("classification_code"),
    source_string(df_bronze, "criterio").alias(
        "confirmation_criterion_code"
    ),
    source_string(df_bronze, "evolucao").alias("case_outcome_code"),
    source_string(df_bronze, "hospitaliz").alias(
        "hospitalization_code"
    ),
    to_date(source_string(df_bronze, "dt_interna")).alias(
        "hospitalization_date"
    ),
    to_date(source_string(df_bronze, "dt_obito")).alias("death_date"),
    source_string(df_bronze, "tpautocto").alias("autochthonous_code"),
    source_string(df_bronze, "sorotipo").alias("serotype_code"),
)

# Código zero não representa um município IBGE válido.
df_cases = df_cases.withColumn(
    "infection_municipality_code_sinan",
    when(
        col("infection_municipality_code_sinan") == lit("0"),
        lit(None).cast("string"),
    ).otherwise(col("infection_municipality_code_sinan")),
)

df_cases = (
    df_cases.join(
        broadcast(location_projection(df_ibge, "residence")),
        col("residence_municipality_code_sinan")
        == col("_residence_join_code"),
        "left",
    )
    .drop("_residence_join_code")
    .join(
        broadcast(location_projection(df_ibge, "notification")),
        col("notification_municipality_code_sinan")
        == col("_notification_join_code"),
        "left",
    )
    .drop("_notification_join_code")
    .join(
        broadcast(location_projection(df_ibge, "infection")),
        col("infection_municipality_code_sinan")
        == col("_infection_join_code"),
        "left",
    )
    .drop("_infection_join_code")
)

df_cases = (
    df_cases.withColumn(
        "age_unit_code",
        substring(col("age_encoded"), 1, 1),
    )
    .withColumn(
        "age_value",
        substring(col("age_encoded"), 2, 3).cast("int"),
    )
    .withColumn("age_unit_name", map_code("age_unit_code", AGE_UNIT_MAPPING))
    .withColumn(
        "age_years",
        when(col("age_unit_code") == lit("4"), col("age_value"))
        .when(col("age_unit_code").isin("1", "2", "3"), lit(0))
        .otherwise(lit(None).cast("int")),
    )
    .withColumn(
        "age_group_name",
        when(col("age_years") == 0, lit("Menor de 1 ano"))
        .when(col("age_years").between(1, 4), lit("1 a 4 anos"))
        .when(col("age_years").between(5, 9), lit("5 a 9 anos"))
        .when(col("age_years").between(10, 14), lit("10 a 14 anos"))
        .when(col("age_years").between(15, 19), lit("15 a 19 anos"))
        .when(col("age_years").between(20, 29), lit("20 a 29 anos"))
        .when(col("age_years").between(30, 39), lit("30 a 39 anos"))
        .when(col("age_years").between(40, 49), lit("40 a 49 anos"))
        .when(col("age_years").between(50, 59), lit("50 a 59 anos"))
        .when(col("age_years").between(60, 69), lit("60 a 69 anos"))
        .when(col("age_years").between(70, 79), lit("70 a 79 anos"))
        .when(col("age_years") >= 80, lit("80 anos ou mais"))
        .otherwise(lit("Ignorada")),
    )
    .withColumn("sex_name", map_code("sex_code", SEX_MAPPING))
    .withColumn(
        "pregnancy_name",
        map_code("pregnancy_code", PREGNANCY_MAPPING),
    )
    .withColumn("race_name", map_code("race_code", RACE_MAPPING))
    .withColumn(
        "education_name",
        map_code("education_code", EDUCATION_MAPPING),
    )
    .withColumn(
        "classification_name",
        map_code("classification_code", CLASSIFICATION_MAPPING),
    )
    .withColumn(
        "confirmation_criterion_name",
        map_code(
            "confirmation_criterion_code",
            CONFIRMATION_CRITERION_MAPPING,
        ),
    )
    .withColumn(
        "case_outcome_name",
        map_code("case_outcome_code", CASE_OUTCOME_MAPPING),
    )
    .withColumn(
        "hospitalization_name",
        map_code("hospitalization_code", HOSPITALIZATION_MAPPING),
    )
    .withColumn(
        "autochthonous_name",
        map_code("autochthonous_code", AUTOCHTHONOUS_MAPPING),
    )
)

df_cases = (
    df_cases.withColumn(
        "is_confirmed_case",
        when(
            (col("disease_name") == lit("dengue"))
            & col("classification_code").isin("10", "11", "12"),
            lit(True),
        )
        .when(
            (col("disease_name") == lit("chikungunya"))
            & (col("classification_code") == lit("13")),
            lit(True),
        )
        .when(col("classification_code").isin("5", "8"), lit(False))
        .otherwise(lit(None).cast("boolean")),
    )
    .withColumn(
        "is_discarded_case",
        when(col("classification_code").isin("5", "8"), lit(True))
        .when(
            col("classification_code").isin("10", "11", "12", "13"),
            lit(False),
        )
        .otherwise(lit(None).cast("boolean")),
    )
    .withColumn(
        "is_alarm_case",
        when(col("classification_code") == lit("11"), lit(True))
        .when(col("classification_code").isNotNull(), lit(False))
        .otherwise(lit(None).cast("boolean")),
    )
    .withColumn(
        "is_severe_case",
        when(col("classification_code") == lit("12"), lit(True))
        .when(col("classification_code").isNotNull(), lit(False))
        .otherwise(lit(None).cast("boolean")),
    )
    .withColumn(
        "is_under_investigation",
        when(
            (col("confirmation_criterion_code") == lit("3"))
            | col("classification_code").isNull(),
            lit(True),
        ).otherwise(lit(False)),
    )
    .withColumn(
        "is_hospitalized",
        when(col("hospitalization_code") == lit("1"), lit(True))
        .when(col("hospitalization_code") == lit("2"), lit(False))
        .otherwise(lit(None).cast("boolean")),
    )
    .withColumn(
        "is_death_by_disease",
        col("case_outcome_code") == lit("2"),
    )
    .withColumn(
        "is_death_other_cause",
        col("case_outcome_code") == lit("3"),
    )
    .withColumn(
        "is_autochthonous",
        when(col("autochthonous_code") == lit("1"), lit(True))
        .when(col("autochthonous_code") == lit("2"), lit(False))
        .otherwise(lit(None).cast("boolean")),
    )
)

df_cases = (
    df_cases.withColumn(
        "record_id",
        sha2(
            concat_ws(
                "||",
                coalesce(col("source_system"), lit("<null>")),
                coalesce(
                    col("source_reference_year").cast("string"),
                    lit("<null>"),
                ),
                coalesce(col("record_hash"), lit("<null>")),
            ),
            256,
        ),
    )
    .withColumn("silver_loaded_at", current_timestamp())
    .withColumn("environment", lit(environment))
    .withColumn(
        "notification_month",
        date_format(col("notification_date"), "MM"),
    )
)

df_cases = df_cases.withColumn(
    "quality_error_codes",
    array_filter(
        array(
            when(
                col("disease_name").isNull()
                | (col("disease_name") == lit("unknown")),
                lit("UNKNOWN_DISEASE"),
            ),
            when(
                col("notification_date").isNull(),
                lit("INVALID_NOTIFICATION_DATE"),
            ),
            when(
                col("notification_date") > current_date(),
                lit("FUTURE_NOTIFICATION_DATE"),
            ),
            when(
                col("notification_date")
                < lit("2000-01-01").cast("date"),
                lit("IMPLAUSIBLE_NOTIFICATION_DATE"),
            ),
            when(
                col("residence_municipality_code_sinan").isNull(),
                lit("MISSING_RESIDENCE_MUNICIPALITY"),
            ),
            when(
                col("residence_municipality_code_sinan").isNotNull()
                & col("residence_municipality_code_ibge").isNull(),
                lit("RESIDENCE_MUNICIPALITY_NOT_FOUND"),
            ),
            when(
                col("source_system").isNull()
                | col("source_batch_id").isNull()
                | col("source_reference_year").isNull()
                | col("source_file").isNull()
                | col("record_hash").isNull(),
                lit("MISSING_SOURCE_IDENTITY"),
            ),
            when(
                col("source_batch_id").isNotNull()
                & (col("source_batch_id") != lit(batch_id)),
                lit("BATCH_ID_MISMATCH"),
            ),
            when(
                col("symptoms_start_date").isNotNull()
                & col("notification_date").isNotNull()
                & (col("symptoms_start_date") > col("notification_date")),
                lit("SYMPTOMS_AFTER_NOTIFICATION"),
            ),
            when(
                col("investigation_date").isNotNull()
                & col("notification_date").isNotNull()
                & (col("investigation_date") < col("notification_date")),
                lit("INVESTIGATION_BEFORE_NOTIFICATION"),
            ),
            when(
                col("closure_date").isNotNull()
                & col("investigation_date").isNotNull()
                & (col("closure_date") < col("investigation_date")),
                lit("CLOSURE_BEFORE_INVESTIGATION"),
            ),
            when(
                col("death_date").isNotNull()
                & col("symptoms_start_date").isNotNull()
                & (col("death_date") < col("symptoms_start_date")),
                lit("DEATH_BEFORE_SYMPTOMS"),
            ),
            when(
                col("investigation_date").isNotNull()
                & (
                    (col("investigation_date") < lit("2000-01-01").cast("date"))
                    | (col("investigation_date") > current_date())
                ),
                lit("IMPLAUSIBLE_INVESTIGATION_DATE"),
            ),
            when(
                col("digitization_date").isNotNull()
                & (
                    (col("digitization_date") < lit("2000-01-01").cast("date"))
                    | (col("digitization_date") > current_date())
                ),
                lit("IMPLAUSIBLE_DIGITIZATION_DATE"),
            ),
            when(
                col("closure_date").isNotNull()
                & (
                    (col("closure_date") < lit("2000-01-01").cast("date"))
                    | (col("closure_date") > current_date())
                ),
                lit("IMPLAUSIBLE_CLOSURE_DATE"),
            ),
            when(
                col("hospitalization_date").isNotNull()
                & (
                    (col("hospitalization_date") < lit("2000-01-01").cast("date"))
                    | (col("hospitalization_date") > current_date())
                ),
                lit("IMPLAUSIBLE_HOSPITALIZATION_DATE"),
            ),
            when(
                col("death_date").isNotNull()
                & (
                    (col("death_date") < lit("2000-01-01").cast("date"))
                    | (col("death_date") > current_date())
                ),
                lit("IMPLAUSIBLE_DEATH_DATE"),
            ),
            when(
                col("notification_year").isNotNull()
                & col("notification_date").isNotNull()
                & (
                    col("notification_year")
                    != spark_year(col("notification_date"))
                ),
                lit("NOTIFICATION_YEAR_MISMATCH"),
            ),
        ),
        lambda error_code: error_code.isNotNull(),
    ),
)

df_cases = df_cases.withColumn(
    "quality_warning_codes",
    array_filter(
        array(
            when(
                col("classification_code").isNull(),
                lit("MISSING_CLASSIFICATION"),
            ),
            when(
                col("classification_name") == lit("Não mapeado"),
                lit("UNMAPPED_CLASSIFICATION"),
            ),
            when(
                col("confirmation_criterion_code").isNull(),
                lit("MISSING_CONFIRMATION_CRITERION"),
            ),
            when(
                col("case_outcome_code").isNull(),
                lit("MISSING_CASE_OUTCOME"),
            ),
            when(
                col("hospitalization_code").isNull()
                | (col("hospitalization_code") == lit("9")),
                lit("UNKNOWN_HOSPITALIZATION"),
            ),
            when(
                col("notification_municipality_code_sinan").isNotNull()
                & col("notification_municipality_code_ibge").isNull(),
                lit("NOTIFICATION_MUNICIPALITY_NOT_FOUND"),
            ),
            when(
                col("infection_municipality_code_sinan").isNotNull()
                & col("infection_municipality_code_ibge").isNull(),
                lit("INFECTION_MUNICIPALITY_NOT_FOUND"),
            ),
            when(
                col("age_encoded").isNotNull()
                & ~col("age_unit_code").isin("1", "2", "3", "4"),
                lit("INVALID_AGE_UNIT"),
            ),
            when(
                col("source_reference_year").isNotNull()
                & col("notification_year").isNotNull()
                & (
                    col("source_reference_year")
                    != col("notification_year")
                ),
                lit("REFERENCE_YEAR_DIFFERS_FROM_NOTIFICATION_YEAR"),
            ),
        ),
        lambda warning_code: warning_code.isNotNull(),
    ),
)

# Como a fonte nao publica um identificador estavel, somente duplicatas exatas
# das 121 colunas recebem a mesma identidade tecnica.
deduplication_window = Window.partitionBy("record_id").orderBy(
    col("bronze_loaded_at").desc_nulls_last(),
    col("source_file").desc_nulls_last(),
)

df_cases = df_cases.withColumn(
    "_duplicate_rank",
    row_number().over(deduplication_window),
)

df_cases = df_cases.withColumn(
    "quality_error_codes",
    when(
        col("_duplicate_rank") > lit(1),
        array_union(
            col("quality_error_codes"),
            array(lit("DUPLICATE_RECORD")),
        ),
    ).otherwise(col("quality_error_codes")),
)

df_cases = df_cases.withColumn(
    "data_quality_status",
    when(size(col("quality_error_codes")) > 0, lit("quarantined"))
    .when(size(col("quality_warning_codes")) > 0, lit("warning"))
    .otherwise(lit("valid")),
)

df_cases = df_cases.persist(StorageLevel.MEMORY_AND_DISK)

try:
    processing_stats = (
        df_cases.agg(
            count(lit(1)).alias("input_record_count"),
            spark_sum(
                when(
                    size(col("quality_error_codes")) == 0,
                    lit(1),
                ).otherwise(lit(0))
            ).alias("silver_record_count"),
            spark_sum(
                when(
                    size(col("quality_error_codes")) > 0,
                    lit(1),
                ).otherwise(lit(0))
            ).alias("quarantine_record_count"),
            spark_sum(
                when(
                    (size(col("quality_error_codes")) == 0)
                    & (size(col("quality_warning_codes")) > 0),
                    lit(1),
                ).otherwise(lit(0))
            ).alias("warning_record_count"),
        )
        .first()
        .asDict()
    )

    logger.info(
        {
            "event": "silver_dengue_cases_statistics",
            "job_name": job_name,
            "batch_id": batch_id,
            **processing_stats,
        }
    )

    if processing_stats["silver_record_count"] == 0:
        raise ValueError("No valid records available for the Silver layer.")

    df_silver = (
        df_cases.filter(size(col("quality_error_codes")) == 0)
        .drop("quality_error_codes", "_duplicate_rank")
    )

    (
        df_silver.repartition(
            "processing_date",
            "granularity",
            "reference_period",
        )
        .write.mode(write_mode)
        .option("compression", "snappy")
        .partitionBy(
            "processing_date",
            "granularity",
            "reference_period",
        )
        .parquet(silver_output_path)
    )

    if processing_stats["quarantine_record_count"] > 0:
        df_quarantine = (
            df_cases.filter(size(col("quality_error_codes")) > 0)
            .withColumn(
                "primary_error_code",
                element_at(col("quality_error_codes"), 1),
            )
            .withColumn("quarantined_at", current_timestamp())
            .drop("_duplicate_rank")
        )

        (
            df_quarantine.repartition(
                "processing_date",
                "granularity",
                "reference_period",
                "primary_error_code",
            )
            .write.mode(write_mode)
            .option("compression", "snappy")
            .partitionBy(
                "processing_date",
                "granularity",
                "reference_period",
                "primary_error_code",
            )
            .parquet(quarantine_output_path)
        )

    logger.info(
        {
            "event": "silver_dengue_cases_finished",
            "job_name": job_name,
            "batch_id": batch_id,
            "processing_date": bronze_partition["processing_date"],
            "granularity": bronze_partition["granularity"],
            "reference_period": bronze_partition["reference_period"],
            **processing_stats,
            "silver_output_path": silver_output_path,
            "quarantine_output_path": quarantine_output_path,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )

finally:
    df_cases.unpersist()
