import logging
import sys
import time
from datetime import datetime, timezone

from awsglue.utils import getResolvedOptions
from pyspark import StorageLevel
from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql.functions import (
    coalesce,
    col,
    concat_ws,
    count,
    current_timestamp,
    date_format,
    dayofmonth,
    dayofweek,
    explode,
    expr,
    lit,
    max as spark_max,
    min as spark_min,
    month,
    quarter,
    sequence,
    size,
    weekofyear,
    when,
    xxhash64,
    year,
)


DATE_ROLE_COLUMNS = [
    "notification_date",
    "symptoms_start_date",
    "investigation_date",
    "digitization_date",
    "hospitalization_date",
    "closure_date",
    "death_date",
]

LOCATION_ATTRIBUTES = [
    "municipality_code_sinan",
    "municipality_code_ibge",
    "municipality_name",
    "uf_code",
    "uf_abbreviation",
    "uf_name",
    "region_code",
    "region_abbreviation",
    "region_name",
]

REQUIRED_SILVER_COLUMNS = {
    "record_id",
    "record_hash",
    "environment",
    "source_system",
    "source_reference_year",
    "source_file",
    "bronze_loaded_at",
    "disease_code",
    "disease_name",
    "notification_date",
    "notification_epidemiological_week",
    "symptoms_start_date",
    "symptoms_epidemiological_week",
    "investigation_date",
    "digitization_date",
    "hospitalization_date",
    "closure_date",
    "death_date",
    "residence_municipality_code_ibge",
    "notification_municipality_code_ibge",
    "infection_municipality_code_ibge",
    "age_unit_code",
    "age_unit_name",
    "age_value",
    "age_years",
    "age_group_name",
    "sex_code",
    "sex_name",
    "pregnancy_code",
    "pregnancy_name",
    "race_code",
    "race_name",
    "education_code",
    "education_name",
    "classification_code",
    "classification_name",
    "confirmation_criterion_code",
    "confirmation_criterion_name",
    "case_outcome_code",
    "case_outcome_name",
    "hospitalization_code",
    "hospitalization_name",
    "autochthonous_code",
    "autochthonous_name",
    "serotype_code",
    "is_confirmed_case",
    "is_discarded_case",
    "is_alarm_case",
    "is_severe_case",
    "is_under_investigation",
    "is_hospitalized",
    "is_death_by_disease",
    "is_death_other_cause",
    "is_autochthonous",
    "data_quality_status",
    "quality_warning_codes",
    "silver_loaded_at",
}

for location_role in ("residence", "notification", "infection"):
    REQUIRED_SILVER_COLUMNS.update(
        f"{location_role}_{attribute}" for attribute in LOCATION_ATTRIBUTES
    )


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


def hash_key(*column_names: str) -> Column:
    all_attributes_missing = col(column_names[0]).isNull()
    for column_name in column_names[1:]:
        all_attributes_missing = all_attributes_missing & col(column_name).isNull()

    hashed_value = xxhash64(
        concat_ws(
            "||",
            *[
                coalesce(col(name).cast("string"), lit("<unknown>"))
                for name in column_names
            ],
        )
    )

    return when(all_attributes_missing, lit(-1)).otherwise(hashed_value)


def date_key(column_name: str) -> Column:
    return coalesce(
        date_format(col(column_name), "yyyyMMdd").cast("int"),
        lit(-1),
    )


def location_key(prefix: str) -> Column:
    return coalesce(
        col(f"{prefix}_municipality_code_ibge").cast("long"),
        lit(-1),
    )


def integer_measure(column_name: str) -> Column:
    return when(col(column_name) == lit(True), lit(1)).otherwise(lit(0))


def build_date_dimension(spark: SparkSession, df: DataFrame) -> DataFrame:
    all_dates = None

    for column_name in DATE_ROLE_COLUMNS:
        projection = df.select(col(column_name).alias("calendar_date")).filter(
            col("calendar_date").isNotNull()
        )
        all_dates = (
            projection
            if all_dates is None
            else all_dates.unionByName(projection)
        )

    # O intervalo contínuo usa a data de notificação, já validada na Silver.
    # As outras datas entram como valores distintos para evitar que um outlier
    # gere milhões de dias na dimensão.
    bounds = df.agg(
        spark_min("notification_date").alias("min_date"),
        spark_max("notification_date").alias("max_date"),
    )

    calendar = bounds.select(
        explode(
            sequence(
                col("min_date"),
                col("max_date"),
                expr("interval 1 day"),
            )
        ).alias("calendar_date")
    ).unionByName(all_dates).dropDuplicates(["calendar_date"])

    dimension = calendar.select(
        date_format("calendar_date", "yyyyMMdd").cast("int").alias("date_key"),
        col("calendar_date"),
        year("calendar_date").alias("year"),
        quarter("calendar_date").alias("quarter"),
        month("calendar_date").alias("month"),
        dayofmonth("calendar_date").alias("day"),
        weekofyear("calendar_date").alias("iso_week_of_year"),
        dayofweek("calendar_date").alias("day_of_week"),
        date_format("calendar_date", "yyyy-MM").alias("year_month"),
        when(dayofweek("calendar_date").isin(1, 7), lit(True))
        .otherwise(lit(False))
        .alias("is_weekend"),
    )

    unknown = spark.range(1).select(
        lit(-1).cast("int").alias("date_key"),
        lit(None).cast("date").alias("calendar_date"),
        lit(None).cast("int").alias("year"),
        lit(None).cast("int").alias("quarter"),
        lit(None).cast("int").alias("month"),
        lit(None).cast("int").alias("day"),
        lit(None).cast("int").alias("iso_week_of_year"),
        lit(None).cast("int").alias("day_of_week"),
        lit("Desconhecido").alias("year_month"),
        lit(None).cast("boolean").alias("is_weekend"),
    )

    return unknown.unionByName(dimension)


def location_projection(df: DataFrame, prefix: str) -> DataFrame:
    return df.select(
        *[
            col(f"{prefix}_{attribute}").alias(attribute)
            for attribute in LOCATION_ATTRIBUTES
        ]
    )


def build_location_dimension(spark: SparkSession, df: DataFrame) -> DataFrame:
    dimension = (
        location_projection(df, "residence")
        .unionByName(location_projection(df, "notification"))
        .unionByName(location_projection(df, "infection"))
        .filter(col("municipality_code_ibge").isNotNull())
        .dropDuplicates(["municipality_code_ibge"])
        .select(
            col("municipality_code_ibge").cast("long").alias("location_key"),
            *LOCATION_ATTRIBUTES,
        )
    )

    unknown = spark.range(1).select(
        lit(-1).cast("long").alias("location_key"),
        *[
            lit("Desconhecido").cast("string").alias(attribute)
            for attribute in LOCATION_ATTRIBUTES
        ],
    )

    return unknown.unionByName(dimension)


def build_disease_dimension(spark: SparkSession, df: DataFrame) -> DataFrame:
    dimension = (
        df.select("disease_code", "disease_name")
        .filter(col("disease_code").isNotNull() | col("disease_name").isNotNull())
        .dropDuplicates()
        .withColumn("disease_key", hash_key("disease_code", "disease_name"))
        .select("disease_key", "disease_code", "disease_name")
    )

    unknown = spark.range(1).select(
        lit(-1).cast("long").alias("disease_key"),
        lit("UNKNOWN").alias("disease_code"),
        lit("unknown").alias("disease_name"),
    )

    return unknown.unionByName(dimension)


def build_demographic_dimension(
    spark: SparkSession,
    df: DataFrame,
) -> DataFrame:
    attributes = [
        "age_unit_code",
        "age_unit_name",
        "age_value",
        "age_years",
        "age_group_name",
        "sex_code",
        "sex_name",
        "pregnancy_code",
        "pregnancy_name",
        "race_code",
        "race_name",
        "education_code",
        "education_name",
    ]
    key_attributes = [
        "age_unit_code",
        "age_value",
        "sex_code",
        "pregnancy_code",
        "race_code",
        "education_code",
    ]

    dimension = (
        df.select(*attributes)
        .dropDuplicates()
        .withColumn("demographic_key", hash_key(*key_attributes))
        .filter(col("demographic_key") != lit(-1))
        .select("demographic_key", *attributes)
    )

    unknown = spark.range(1).select(
        lit(-1).cast("long").alias("demographic_key"),
        *[
            (
                lit(None).cast("int").alias(attribute)
                if attribute in {"age_value", "age_years"}
                else lit("Desconhecido").alias(attribute)
            )
            for attribute in attributes
        ],
    )

    return unknown.unionByName(dimension)


def build_clinical_dimension(spark: SparkSession, df: DataFrame) -> DataFrame:
    attributes = [
        "classification_code",
        "classification_name",
        "confirmation_criterion_code",
        "confirmation_criterion_name",
        "case_outcome_code",
        "case_outcome_name",
        "hospitalization_code",
        "hospitalization_name",
        "autochthonous_code",
        "autochthonous_name",
        "serotype_code",
    ]
    key_attributes = [
        "classification_code",
        "confirmation_criterion_code",
        "case_outcome_code",
        "hospitalization_code",
        "autochthonous_code",
        "serotype_code",
    ]

    dimension = (
        df.select(*attributes)
        .dropDuplicates()
        .withColumn("clinical_key", hash_key(*key_attributes))
        .filter(col("clinical_key") != lit(-1))
        .select("clinical_key", *attributes)
    )

    unknown = spark.range(1).select(
        lit(-1).cast("long").alias("clinical_key"),
        *[lit("Desconhecido").alias(attribute) for attribute in attributes],
    )

    return unknown.unionByName(dimension)


def build_fact(df: DataFrame) -> DataFrame:
    demographic_key_columns = [
        "age_unit_code",
        "age_value",
        "sex_code",
        "pregnancy_code",
        "race_code",
        "education_code",
    ]
    clinical_key_columns = [
        "classification_code",
        "confirmation_criterion_code",
        "case_outcome_code",
        "hospitalization_code",
        "autochthonous_code",
        "serotype_code",
    ]

    return df.select(
        col("record_id").alias("case_id"),
        "record_hash",
        "environment",
        hash_key("disease_code", "disease_name").alias("disease_key"),
        date_key("notification_date").alias("notification_date_key"),
        date_key("symptoms_start_date").alias("symptoms_start_date_key"),
        date_key("investigation_date").alias("investigation_date_key"),
        date_key("digitization_date").alias("digitization_date_key"),
        date_key("hospitalization_date").alias("hospitalization_date_key"),
        date_key("closure_date").alias("closure_date_key"),
        date_key("death_date").alias("death_date_key"),
        location_key("residence").alias("residence_location_key"),
        location_key("notification").alias("notification_location_key"),
        location_key("infection").alias("infection_location_key"),
        hash_key(*demographic_key_columns).alias("demographic_key"),
        hash_key(*clinical_key_columns).alias("clinical_key"),
        "notification_epidemiological_week",
        "symptoms_epidemiological_week",
        lit(1).cast("int").alias("notification_count"),
        integer_measure("is_confirmed_case").alias("confirmed_case_count"),
        integer_measure("is_discarded_case").alias("discarded_case_count"),
        integer_measure("is_alarm_case").alias("alarm_case_count"),
        integer_measure("is_severe_case").alias("severe_case_count"),
        integer_measure("is_under_investigation").alias(
            "under_investigation_count"
        ),
        integer_measure("is_hospitalized").alias("hospitalized_case_count"),
        integer_measure("is_death_by_disease").alias(
            "death_by_disease_count"
        ),
        integer_measure("is_death_other_cause").alias(
            "death_other_cause_count"
        ),
        integer_measure("is_autochthonous").alias("autochthonous_case_count"),
        when(size(col("quality_warning_codes")) > 0, lit(1))
        .otherwise(lit(0))
        .alias("quality_warning_count"),
        "data_quality_status",
        "quality_warning_codes",
        "source_system",
        "source_reference_year",
        "source_file",
        "bronze_loaded_at",
        "silver_loaded_at",
        current_timestamp().alias("gold_loaded_at"),
        year("notification_date").alias("notification_year"),
        date_format("notification_date", "MM").alias("notification_month"),
    )


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "ENVIRONMENT",
        "SILVER_INPUT_PATH",
        "GOLD_OUTPUT_PATH",
        "WRITE_MODE",
    ],
)

job_name = args["JOB_NAME"]
environment = args["ENVIRONMENT"]
silver_input_path = args["SILVER_INPUT_PATH"]
gold_output_path = args["GOLD_OUTPUT_PATH"].rstrip("/")
write_mode = args["WRITE_MODE"].lower()

if write_mode != "overwrite":
    raise ValueError(
        f"Invalid WRITE_MODE: {write_mode}. The Gold snapshot requires overwrite."
    )

logger = configure_logger(job_name)
spark = SparkSession.builder.appName(job_name).getOrCreate()

spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.parquet.compression.codec", "snappy")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "static")
spark.conf.set("spark.sql.shuffle.partitions", "48")

logger.info(
    {
        "event": "gold_dengue_star_schema_started",
        "job_name": job_name,
        "environment": environment,
        "silver_input_path": silver_input_path,
        "gold_output_path": gold_output_path,
        "write_mode": write_mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

df_silver = spark.read.parquet(silver_input_path)
missing_columns = sorted(REQUIRED_SILVER_COLUMNS.difference(df_silver.columns))

if missing_columns:
    raise ValueError(
        "Missing required Silver columns: " + ", ".join(missing_columns)
    )

# A Gold aceita registros Silver válidos e com warning. Registros em quarentena
# não estão no path Silver e, portanto, não entram no modelo dimensional.
df_cases = df_silver.filter(
    col("data_quality_status").isin("valid", "warning")
).persist(StorageLevel.MEMORY_AND_DISK)

try:
    record_count = df_cases.count()
    duplicate_case_count = (
        df_cases.groupBy("record_id")
        .agg(count(lit(1)).alias("record_count"))
        .filter(col("record_count") > 1)
        .count()
    )

    if record_count == 0:
        raise ValueError("No Silver records available for the Gold layer.")

    if duplicate_case_count > 0:
        raise ValueError(
            f"Gold grain violation: {duplicate_case_count} duplicate record_id values."
        )

    dimensions = {
        "dim_date": build_date_dimension(spark, df_cases),
        "dim_location": build_location_dimension(spark, df_cases),
        "dim_disease": build_disease_dimension(spark, df_cases),
        "dim_demographic": build_demographic_dimension(spark, df_cases),
        "dim_clinical": build_clinical_dimension(spark, df_cases),
    }

    for table_name, dimension in dimensions.items():
        (
            dimension.coalesce(1)
            .write.mode("overwrite")
            .option("compression", "snappy")
            .parquet(f"{gold_output_path}/{table_name}/")
        )

    fact = build_fact(df_cases)
    (
        fact.repartition("notification_year", "notification_month")
        .write.mode(write_mode)
        .option("compression", "snappy")
        .partitionBy("notification_year", "notification_month")
        .parquet(f"{gold_output_path}/fact_dengue_cases/")
    )

    logger.info(
        {
            "event": "gold_dengue_star_schema_finished",
            "job_name": job_name,
            "environment": environment,
            "record_count": record_count,
            "duplicate_case_count": duplicate_case_count,
            "tables": [*dimensions.keys(), "fact_dengue_cases"],
            "gold_output_path": gold_output_path,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )
finally:
    df_cases.unpersist()