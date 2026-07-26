import logging
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

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
    row_number,
    sequence,
    size,
    weekofyear,
    when,
    xxhash64,
    year,
)
from pyspark.sql.window import Window


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
    "source_batch_id",
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
    "ingestion_source",
    "source_extraction_batch_id",
    "source_manifest",
    "processing_date",
    "granularity",
    "reference_period",
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


def parse_silver_partition_path(silver_input_path: str) -> dict[str, str]:
    parsed = urlparse(silver_input_path.rstrip("/"))

    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(
            "SILVER_INPUT_PATH must be an S3 URI for one processing partition."
        )

    pattern = re.compile(
        r"^(?P<base_path>.+)/"
        r"processing_date=(?P<processing_date>[0-9]{4}-[0-9]{2}-[0-9]{2})/"
        r"granularity=(?P<granularity>day|month)/"
        r"reference_period=(?P<reference_period>"
        r"(?:[0-9]{4}-[0-9]{2}-[0-9]{2})|(?:[0-9]{4}-[0-9]{2})"
        r")/?$"
    )
    match = pattern.match(parsed.path.lstrip("/"))

    if not match:
        raise ValueError(
            "SILVER_INPUT_PATH must end with "
            "processing_date=YYYY-MM-DD/granularity=day|month/"
            "reference_period=YYYY-MM-DD|YYYY-MM."
        )

    values = match.groupdict()
    if values["granularity"] == "day" and len(values["reference_period"]) != 10:
        raise ValueError("Daily Silver input requires reference_period=YYYY-MM-DD.")
    if values["granularity"] == "month" and len(values["reference_period"]) != 7:
        raise ValueError("Monthly Silver input requires reference_period=YYYY-MM.")

    values["base_uri"] = f"s3://{parsed.netloc}/{values['base_path']}"
    return values


def validate_required_columns(df: DataFrame, dataset_name: str) -> None:
    missing_columns = sorted(REQUIRED_SILVER_COLUMNS.difference(df.columns))

    if missing_columns:
        raise ValueError(
            f"Missing required columns in {dataset_name}: "
            + ", ".join(missing_columns)
        )


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
        "source_batch_id",
        "source_extraction_batch_id",
        "source_manifest",
        "ingestion_source",
        "processing_date",
        "granularity",
        "reference_period",
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
        "BATCH_ID",
        "ENVIRONMENT",
        "SILVER_INPUT_PATH",
        "SILVER_ROOT_PATH",
        "GOLD_OUTPUT_PATH",
        "WRITE_MODE",
    ],
)

job_name = args["JOB_NAME"]
batch_id = args["BATCH_ID"]
environment = args["ENVIRONMENT"]
silver_input_path = args["SILVER_INPUT_PATH"]
silver_root_path = args["SILVER_ROOT_PATH"].rstrip("/")
gold_output_path = args["GOLD_OUTPUT_PATH"].rstrip("/")
write_mode = args["WRITE_MODE"].lower()
silver_partition = parse_silver_partition_path(silver_input_path)

if silver_partition["base_uri"].rstrip("/") != silver_root_path:
    raise ValueError(
        "SILVER_INPUT_PATH does not belong to SILVER_ROOT_PATH: "
        f"{silver_input_path} is outside {silver_root_path}."
    )

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
        "event": "dengue_silver_to_gold_started",
        "job_name": job_name,
        "batch_id": batch_id,
        "environment": environment,
        "silver_input_path": silver_input_path,
        "silver_root_path": silver_root_path,
        "processing_date": silver_partition["processing_date"],
        "granularity": silver_partition["granularity"],
        "reference_period": silver_partition["reference_period"],
        "gold_output_path": gold_output_path,
        "write_mode": write_mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

df_current_batch = (
    spark.read.option("basePath", silver_root_path).parquet(silver_input_path)
)
validate_required_columns(df_current_batch, "current Silver partition")

current_partition_record_count = df_current_batch.count()
if current_partition_record_count == 0:
    raise ValueError(f"No Silver records found in {silver_input_path}.")

batch_id_mismatch_count = df_current_batch.filter(
    col("source_batch_id").isNull()
    | (col("source_batch_id") != lit(batch_id))
).count()

if batch_id_mismatch_count > 0:
    raise ValueError(
        "Silver batch identity mismatch: "
        f"{batch_id_mismatch_count} records do not belong to {batch_id}."
    )

# O lote atual valida a identidade da execução. Para preservar dimensões únicas
# e uma fato completa em Parquet, a Gold reconstrói o snapshot a partir da raiz
# Silver. Reprocessamentos são resolvidos pela versão Silver mais recente de
# cada record_id.
df_silver_snapshot = spark.read.parquet(silver_root_path)
validate_required_columns(df_silver_snapshot, "Silver snapshot")

latest_record_window = Window.partitionBy("record_id").orderBy(
    col("silver_loaded_at").desc_nulls_last(),
    col("processing_date").desc_nulls_last(),
    col("source_batch_id").desc_nulls_last(),
)

df_cases = (
    df_silver_snapshot.filter(
        col("data_quality_status").isin("valid", "warning")
    )
    .withColumn("_gold_record_version", row_number().over(latest_record_window))
    .filter(col("_gold_record_version") == 1)
    .drop("_gold_record_version")
    .persist(StorageLevel.MEMORY_AND_DISK)
)

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
            "event": "dengue_silver_to_gold_finished",
            "job_name": job_name,
            "batch_id": batch_id,
            "environment": environment,
            "current_partition_record_count": current_partition_record_count,
            "record_count": record_count,
            "duplicate_case_count": duplicate_case_count,
            "tables": [*dimensions.keys(), "fact_dengue_cases"],
            "gold_output_path": gold_output_path,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )
finally:
    df_cases.unpersist()
