import logging
import sys
import time
from datetime import datetime, timezone

from awsglue.utils import getResolvedOptions
from pyspark import StorageLevel
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    coalesce,
    count,
    current_timestamp,
    date_format,
    input_file_name,
    lit,
    lower,
    regexp_extract,
    sum as spark_sum,
    to_date,
    trim,
    when,
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

        # Garante que o horário exibido com "Z" esteja realmente em UTC.
        formatter.converter = time.gmtime

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "ENVIRONMENT",
        "STAGING_INPUT_PATH",
        "BRONZE_OUTPUT_PATH",
        "PARTITION_DATE_COLUMN",
        "WRITE_MODE",
    ],
)

job_name = args["JOB_NAME"]
environment = args["ENVIRONMENT"]
staging_input_path = args["STAGING_INPUT_PATH"]
bronze_output_path = args["BRONZE_OUTPUT_PATH"]
partition_date_column = args["PARTITION_DATE_COLUMN"]
write_mode = args["WRITE_MODE"].lower()

valid_write_modes = {"append", "overwrite"}

if write_mode not in valid_write_modes:
    raise ValueError(
        f"Invalid WRITE_MODE: {write_mode}. "
        f"Expected one of: {sorted(valid_write_modes)}"
    )

logger = configure_logger(job_name)

spark = SparkSession.builder.appName(job_name).getOrCreate()

spark.conf.set("spark.sql.parquet.compression.codec", "snappy")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
spark.conf.set("spark.sql.shuffle.partitions", "8")

logger.info(
    {
        "event": "bronze_ingestion_started",
        "job_name": job_name,
        "environment": environment,
        "staging_input_path": staging_input_path,
        "bronze_output_path": bronze_output_path,
        "partition_date_column": partition_date_column,
        "write_mode": write_mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

# JSONL corresponde a um objeto JSON por linha.
df = (
    spark.read
    .option("multiLine", "false")
    .json(staging_input_path)
)

if not df.columns:
    raise ValueError(
        f"No columns found in input path: {staging_input_path}"
    )

# ------------------------------------------------------------------
# Metadados técnicos da Bronze
# ------------------------------------------------------------------

df = df.withColumn("_source_file", input_file_name())

df = df.withColumn(
    "_staging_extract_date",
    to_date(
        regexp_extract(
            col("_source_file"),
            r"extract_date=([0-9]{4}-[0-9]{2}-[0-9]{2})",
            1,
        )
    ),
)

# ------------------------------------------------------------------
# Identificação da doença
#
# A doença é identificada pelo metadado da extração.
# ------------------------------------------------------------------

if "_source" not in df.columns:
    logger.warning(
        {
            "event": "source_column_not_found",
            "job_name": job_name,
            "source_column": "_source",
            "action": (
                "records_will_be_written_to_unknown_disease_partition"
            ),
        }
    )

    df = df.withColumn("disease", lit("unknown"))

else:
    source_normalized = lower(
        trim(col("_source").cast("string"))
    )

    df = df.withColumn(
        "disease",
        when(
            source_normalized.contains("dengue"),
            lit("dengue"),
        )
        .when(
            source_normalized.contains("zika"),
            lit("zika"),
        )
        .when(
            source_normalized.contains("chikungunya"),
            lit("chikungunya"),
        )
        .otherwise(lit("unknown")),
    )

# ------------------------------------------------------------------
# Particionamento mensal pela data de notificação
#
# Valores ausentes ou inválidos são preservados em:
# year=unknown/month=unknown
# ------------------------------------------------------------------

if partition_date_column not in df.columns:
    logger.warning(
        {
            "event": "partition_date_column_not_found",
            "job_name": job_name,
            "partition_date_column": partition_date_column,
            "action": (
                "records_will_be_written_to_unknown_date_partition"
            ),
        }
    )

    df = (
        df.withColumn(
            "_partition_date",
            lit(None).cast("date"),
        )
        .withColumn("year", lit("unknown"))
        .withColumn("month", lit("unknown"))
    )

else:
    df = df.withColumn(
        "_partition_date",
        to_date(
            trim(col(partition_date_column).cast("string"))
        ),
    )

    df = (
        df.withColumn(
            "year",
            when(
                col("_partition_date").isNotNull(),
                date_format(col("_partition_date"), "yyyy"),
            ).otherwise(lit("unknown")),
        )
        .withColumn(
            "month",
            when(
                col("_partition_date").isNotNull(),
                date_format(col("_partition_date"), "MM"),
            ).otherwise(lit("unknown")),
        )
    )

df = (
    df.withColumn("_bronze_loaded_at", current_timestamp())
    .withColumn("_environment", lit(environment))
)

# Evita que o count e a escrita releiam todo o JSONL separadamente.
df = df.persist(StorageLevel.MEMORY_AND_DISK)

try:
    ingestion_stats = (
        df.agg(
            count(lit(1)).alias("record_count"),
            coalesce(
                spark_sum(
                    when(
                        col("disease") == "unknown",
                        lit(1),
                    ).otherwise(lit(0))
                ),
                lit(0),
            ).alias("unknown_disease_count"),
            coalesce(
                spark_sum(
                    when(
                        col("_partition_date").isNull(),
                        lit(1),
                    ).otherwise(lit(0))
                ),
                lit(0),
            ).alias("unknown_partition_date_count"),
        )
        .first()
        .asDict()
    )

    logger.info(
        {
            "event": "bronze_ingestion_statistics",
            "job_name": job_name,
            **ingestion_stats,
        }
    )

    (
        df.repartition("disease", "year", "month")
        .write
        .mode(write_mode)
        .option("compression", "snappy")
        .partitionBy("disease", "year", "month")
        .parquet(bronze_output_path)
    )

    logger.info(
        {
            "event": "bronze_ingestion_finished",
            "job_name": job_name,
            "record_count": ingestion_stats["record_count"],
            "unknown_disease_count": (
                ingestion_stats["unknown_disease_count"]
            ),
            "unknown_partition_date_count": (
                ingestion_stats["unknown_partition_date_count"]
            ),
            "bronze_output_path": bronze_output_path,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )

finally:
    df.unpersist()