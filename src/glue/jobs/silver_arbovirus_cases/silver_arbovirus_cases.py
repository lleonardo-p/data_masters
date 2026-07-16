import logging
import sys
import time
from datetime import datetime, timezone

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
    "8": "Descartado (cÃ³digo legado)",
    "10": "Dengue",
    "11": "Dengue com sinais de alarme",
    "12": "Dengue grave",
    "13": "Chikungunya",
}

CONFIRMATION_CRITERION_MAPPING = {
    "1": "Laboratorial",
    "2": "ClÃ­nico-epidemiolÃ³gico",
    "3": "Em investigaÃ§Ã£o",
}

CASE_OUTCOME_MAPPING = {
    "1": "Cura",
    "2": "Ã“bito pelo agravo",
    "3": "Ã“bito por outras causas",
    "4": "Ã“bito em investigaÃ§Ã£o",
    "9": "Ignorado",
}

SEX_MAPPING = {
    "M": "Masculino",
    "F": "Feminino",
    "I": "Ignorado",
}

PREGNANCY_MAPPING = {
    "1": "1Âº trimestre",
    "2": "2Âº trimestre",
    "3": "3Âº trimestre",
    "4": "Idade gestacional ignorada",
    "5": "NÃ£o",
    "6": "NÃ£o se aplica",
    "9": "Ignorado",
}

RACE_MAPPING = {
    "1": "Branca",
    "2": "Preta",
    "3": "Amarela",
    "4": "Parda",
    "5": "IndÃ­gena",
    "9": "Ignorado",
}

EDUCATION_MAPPING = {
    "0": "Analfabeto",
    "1": "1Âª a 4Âª sÃ©rie incompleta do ensino fundamental",
    "2": "4Âª sÃ©rie completa do ensino fundamental",
    "3": "5Âª a 8Âª sÃ©rie incompleta do ensino fundamental",
    "4": "Ensino fundamental completo",
    "5": "Ensino mÃ©dio incompleto",
    "6": "Ensino mÃ©dio completo",
    "7": "EducaÃ§Ã£o superior incompleta",
    "8": "EducaÃ§Ã£o superior completa",
    "9": "Ignorado",
    "10": "NÃ£o se aplica",
}

AGE_UNIT_MAPPING = {
    "1": "Hora",
    "2": "Dia",
    "3": "MÃªs",
    "4": "Ano",
}

HOSPITALIZATION_MAPPING = {
    "1": "Sim",
    "2": "NÃ£o",
    "9": "Ignorado",
}

AUTOCHTHONOUS_MAPPING = {
    "1": "Sim",
    "2": "NÃ£o",
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

    return expression.otherwise(lit("NÃ£o mapeado"))


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


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "ENVIRONMENT",
        "BRONZE_INPUT_PATH",
        "IBGE_REFERENCE_PATH",
        "SILVER_OUTPUT_PATH",
        "QUARANTINE_OUTPUT_PATH",
        "WRITE_MODE",
    ],
)

job_name = args["JOB_NAME"]
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

spark.conf.set("spark.sql.parquet.compression.codec", "snappy")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
spark.conf.set("spark.sql.shuffle.partitions", "8")

logger.info(
    {
        "event": "silver_arbovirus_cases_started",
        "job_name": job_name,
        "environment": environment,
        "bronze_input_path": bronze_input_path,
        "ibge_reference_path": ibge_reference_path,
        "silver_output_path": silver_output_path,
        "quarantine_output_path": quarantine_output_path,
        "write_mode": write_mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

df_bronze = spark.read.parquet(bronze_input_path)

required_bronze_columns = {
    "_source",
    "_api_offset_page",
    "_api_row_number",
    "disease",
    "id_agravo",
    "dt_notific",
    "id_mn_resi",
}

missing_bronze_columns = sorted(
    required_bronze_columns.difference(df_bronze.columns)
)

if missing_bronze_columns:
    raise ValueError(
        "Missing required Bronze columns: "
        f"{', '.join(missing_bronze_columns)}"
    )

# O arquivo do IBGE Ã© um Ãºnico array JSON, por isso multiLine=true.
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

# SeleÃ§Ã£o e tipagem do contrato Silver. Colunas nÃ£o usadas pela Gold continuam
# preservadas na Bronze e podem ser adicionadas em versÃµes futuras do contrato.
df_cases = df_bronze.select(
    source_string(df_bronze, "_source").alias("source_system"),
    source_string(df_bronze, "_nu_ano_param")
    .cast("int")
    .alias("source_reference_year"),
    source_string(df_bronze, "_api_offset_page")
    .cast("long")
    .alias("source_offset"),
    source_string(df_bronze, "_api_row_number")
    .cast("int")
    .alias("source_row_number"),
    to_timestamp(
        source_string(df_bronze, "_extraction_datetime_utc")
    ).alias("extracted_at"),
    source_string(df_bronze, "_source_file").alias("source_file"),
    to_timestamp(source_string(df_bronze, "_bronze_loaded_at")).alias(
        "bronze_loaded_at"
    ),
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

# CÃ³digo zero nÃ£o representa um municÃ­pio IBGE vÃ¡lido.
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
        when(col("age_unit_code") == lit("4"), col("age_value")).otherwise(
            lit(None).cast("int")
        ),
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

record_id_columns = [
    "source_system",
    "source_reference_year",
    "source_offset",
    "source_row_number",
]

record_hash_columns = [
    "disease_name",
    "disease_code",
    "notification_date",
    "symptoms_start_date",
    "residence_municipality_code_sinan",
    "notification_municipality_code_sinan",
    "health_unit_code",
    "birth_year",
    "age_encoded",
    "sex_code",
    "classification_code",
    "confirmation_criterion_code",
    "case_outcome_code",
    "hospitalization_code",
]

df_cases = (
    df_cases.withColumn(
        "record_id",
        sha2(
            concat_ws(
                "||",
                *[
                    coalesce(col(name).cast("string"), lit("<null>"))
                    for name in record_id_columns
                ],
            ),
            256,
        ),
    )
    .withColumn(
        "record_hash",
        sha2(
            concat_ws(
                "||",
                *[
                    coalesce(col(name).cast("string"), lit("<null>"))
                    for name in record_hash_columns
                ],
            ),
            256,
        ),
    )
    .withColumn("silver_loaded_at", current_timestamp())
    .withColumn("environment", lit(environment))
    .withColumn("year", date_format(col("notification_date"), "yyyy"))
    .withColumn("month", date_format(col("notification_date"), "MM"))
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
                | col("source_offset").isNull()
                | col("source_row_number").isNull(),
                lit("MISSING_SOURCE_IDENTITY"),
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
                col("classification_name") == lit("NÃ£o mapeado"),
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
        ),
        lambda warning_code: warning_code.isNotNull(),
    ),
)

# A deduplicaÃ§Ã£o usa a identidade tÃ©cnica da paginaÃ§Ã£o. O hash de conteÃºdo nÃ£o
# Ã© usado como chave porque dois pacientes distintos podem ter atributos iguais.
deduplication_window = Window.partitionBy("record_id").orderBy(
    col("extracted_at").desc_nulls_last(),
    col("source_offset").desc_nulls_last(),
    col("source_row_number").desc_nulls_last(),
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
            "event": "silver_arbovirus_cases_statistics",
            "job_name": job_name,
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
        df_silver.repartition("disease_name", "year", "month")
        .write.mode(write_mode)
        .option("compression", "snappy")
        .partitionBy("disease_name", "year", "month")
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
            .withColumn(
                "quarantine_year",
                date_format(current_date(), "yyyy"),
            )
            .withColumn(
                "quarantine_month",
                date_format(current_date(), "MM"),
            )
            .drop("_duplicate_rank")
        )

        (
            df_quarantine.repartition(
                "primary_error_code",
                "quarantine_year",
                "quarantine_month",
            )
            .write.mode(write_mode)
            .option("compression", "snappy")
            .partitionBy(
                "primary_error_code",
                "quarantine_year",
                "quarantine_month",
            )
            .parquet(quarantine_output_path)
        )

    logger.info(
        {
            "event": "silver_arbovirus_cases_finished",
            "job_name": job_name,
            **processing_stats,
            "silver_output_path": silver_output_path,
            "quarantine_output_path": quarantine_output_path,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )

finally:
    df_cases.unpersist()