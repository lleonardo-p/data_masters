import re
import sys
import unicodedata
from datetime import datetime, timezone

from awsglue.utils import getResolvedOptions
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    coalesce,
    current_date,
    current_timestamp,
    date_format,
    input_file_name,
    lit,
    lower,
    regexp_extract,
    to_date,
    when,
)


def normalize_column_name(column_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", column_name)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.strip().lower()
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.strip("_")

    return normalized or "unknown_column"


def unique_column_names(columns: list[str]) -> list[str]:
    seen = {}
    result = []

    for column in columns:
        base_name = normalize_column_name(column)
        count = seen.get(base_name, 0)

        if count == 0:
            final_name = base_name
        else:
            final_name = f"{base_name}_{count + 1}"

        seen[base_name] = count + 1
        result.append(final_name)

    return result


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
write_mode = args["WRITE_MODE"]

spark = SparkSession.builder.appName(job_name).getOrCreate()

spark.conf.set("spark.sql.parquet.compression.codec", "snappy")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
spark.conf.set("spark.sql.shuffle.partitions", "8")

print(
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

df_raw = spark.read.json(staging_input_path)

if not df_raw.columns:
    raise ValueError(f"No columns found in input path: {staging_input_path}")

original_columns = df_raw.columns
normalized_columns = unique_column_names(original_columns)

df = df_raw.select(
    [
        col(original).alias(normalized)
        for original, normalized in zip(original_columns, normalized_columns)
    ]
)

df = df.withColumn("_source_file", input_file_name())

df = df.withColumn(
    "_staging_extract_date",
    regexp_extract(col("_source_file"), r"extract_date=([0-9]{4}-[0-9]{2}-[0-9]{2})", 1),
)

source_expr = lower(col("_source")) if "_source" in df.columns else lit("")

df = df.withColumn(
    "disease",
    when(source_expr.contains("dengue"), lit("dengue"))
    .when(source_expr.contains("zika"), lit("zika"))
    .when(source_expr.contains("chikungunya"), lit("chikungunya"))
    .otherwise(lit("unknown")),
)

if partition_date_column in df.columns:
    notification_date_expr = to_date(col(partition_date_column))
else:
    notification_date_expr = lit(None).cast("date")

if "_extraction_datetime_utc" in df.columns:
    extraction_date_expr = to_date(col("_extraction_datetime_utc").substr(1, 10))
else:
    extraction_date_expr = lit(None).cast("date")

df = df.withColumn(
    "_partition_date",
    coalesce(notification_date_expr, extraction_date_expr, current_date()),
)

df = (
    df.withColumn("year", date_format(col("_partition_date"), "yyyy"))
    .withColumn("month", date_format(col("_partition_date"), "MM"))
    .withColumn("day", date_format(col("_partition_date"), "dd"))
    .withColumn("_bronze_loaded_at", current_timestamp())
    .withColumn("_environment", lit(environment))
)

record_count = df.count()

print(
    {
        "event": "bronze_ingestion_record_count",
        "job_name": job_name,
        "record_count": record_count,
    }
)

(
    df.repartition("disease", "year", "month", "day")
    .write.mode(write_mode)
    .option("compression", "snappy")
    .partitionBy("disease", "year", "month", "day")
    .parquet(bronze_output_path)
)

print(
    {
        "event": "bronze_ingestion_finished",
        "job_name": job_name,
        "record_count": record_count,
        "bronze_output_path": bronze_output_path,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
)