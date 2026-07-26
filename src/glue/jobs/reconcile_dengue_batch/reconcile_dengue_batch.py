import json
import logging
import re
import sys
import time
from datetime import datetime, timezone

import boto3
from awsglue.utils import getResolvedOptions
from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    count,
    lit,
    row_number,
    sum as spark_sum,
    when,
)
from pyspark.sql.window import Window


DATE_FOREIGN_KEYS = [
    "notification_date_key",
    "symptoms_start_date_key",
    "investigation_date_key",
    "digitization_date_key",
    "hospitalization_date_key",
    "closure_date_key",
    "death_date_key",
]

LOCATION_FOREIGN_KEYS = [
    "residence_location_key",
    "notification_location_key",
    "infection_location_key",
]

MEASURE_COLUMNS = [
    "notification_count",
    "confirmed_case_count",
    "discarded_case_count",
    "alarm_case_count",
    "severe_case_count",
    "under_investigation_count",
    "hospitalized_case_count",
    "death_by_disease_count",
    "death_other_cause_count",
    "autochthonous_case_count",
    "quality_warning_count",
]


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


def path_exists(spark: SparkSession, path: str) -> bool:
    jvm = spark._jvm
    hadoop_configuration = spark._jsc.hadoopConfiguration()
    hadoop_path = jvm.org.apache.hadoop.fs.Path(path)
    return hadoop_path.getFileSystem(hadoop_configuration).exists(hadoop_path)


def require_columns(
    dataframe: DataFrame,
    required_columns: set[str],
    dataset_name: str,
) -> None:
    missing_columns = sorted(required_columns.difference(dataframe.columns))

    if missing_columns:
        raise ValueError(
            f"Missing required {dataset_name} columns: "
            + ", ".join(missing_columns)
        )


def parse_processing_partition(path: str, argument_name: str) -> dict[str, str]:
    pattern = re.compile(
        r"^(?P<root>s3://.+?)/"
        r"processing_date=(?P<processing_date>[0-9]{4}-[0-9]{2}-[0-9]{2})/"
        r"granularity=(?P<granularity>day|month)/"
        r"reference_period=(?P<reference_period>"
        r"(?:[0-9]{4}-[0-9]{2}-[0-9]{2})|(?:[0-9]{4}-[0-9]{2})"
        r")/?$"
    )
    match = pattern.match(path.rstrip("/"))

    if not match:
        raise ValueError(
            f"{argument_name} must point to one processing partition using "
            "processing_date=YYYY-MM-DD/granularity=day|month/"
            "reference_period=YYYY-MM-DD|YYYY-MM."
        )

    metadata = match.groupdict()
    if metadata["granularity"] == "day" and len(
        metadata["reference_period"]
    ) != 10:
        raise ValueError(
            f"{argument_name} daily partition requires YYYY-MM-DD."
        )
    if metadata["granularity"] == "month" and len(
        metadata["reference_period"]
    ) != 7:
        raise ValueError(
            f"{argument_name} monthly partition requires YYYY-MM."
        )

    return metadata


def duplicate_key_count(dataframe: DataFrame, key_column: str) -> int:
    return (
        dataframe.groupBy(key_column)
        .agg(count(lit(1)).alias("record_count"))
        .filter(col("record_count") > 1)
        .count()
    )


def orphan_key_count(
    fact: DataFrame,
    dimension: DataFrame,
    fact_key: str,
    dimension_key: str,
) -> int:
    fact_keys = fact.select(col(fact_key).alias("_key")).distinct()
    dimension_keys = dimension.select(
        col(dimension_key).alias("_key")
    ).distinct()

    return fact_keys.join(dimension_keys, "_key", "left_anti").count()


def write_json_report(
    s3_prefix: str,
    batch_identifier: str,
    report: dict,
) -> str:
    if not s3_prefix.startswith("s3://"):
        raise ValueError(
            "RECONCILIATION_OUTPUT_PATH must be an s3:// URI."
        )

    bucket_and_key = s3_prefix.removeprefix("s3://")
    bucket_name, separator, key_prefix = bucket_and_key.partition("/")

    if not bucket_name or not separator:
        raise ValueError(
            "RECONCILIATION_OUTPUT_PATH must include a bucket and prefix."
        )

    safe_batch_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", batch_identifier)
    report_key = (
        f"{key_prefix.rstrip('/')}/batch_id={safe_batch_id}/"
        "reconciliation.json"
    )
    report_body = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ).encode("utf-8")

    boto3.client("s3").put_object(
        Bucket=bucket_name,
        Key=report_key,
        Body=report_body,
        ContentType="application/json",
    )

    return f"s3://{bucket_name}/{report_key}"


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "BATCH_ID",
        "ENVIRONMENT",
        "BRONZE_INPUT_PATH",
        "SILVER_INPUT_PATH",
        "SILVER_ROOT_PATH",
        "QUARANTINE_ROOT_PATH",
        "GOLD_INPUT_PATH",
        "RECONCILIATION_OUTPUT_PATH",
        "FAIL_ON_MISMATCH",
    ],
)

job_name = args["JOB_NAME"]
batch_id = args["BATCH_ID"]
environment = args["ENVIRONMENT"]
bronze_input_path = args["BRONZE_INPUT_PATH"].rstrip("/")
silver_input_path = args["SILVER_INPUT_PATH"].rstrip("/")
silver_root_path = args["SILVER_ROOT_PATH"].rstrip("/")
quarantine_root_path = args["QUARANTINE_ROOT_PATH"].rstrip("/")
gold_input_path = args["GOLD_INPUT_PATH"].rstrip("/")
reconciliation_output_path = args["RECONCILIATION_OUTPUT_PATH"].rstrip("/")
fail_on_mismatch = args["FAIL_ON_MISMATCH"].lower() == "true"

bronze_partition = parse_processing_partition(
    bronze_input_path,
    "BRONZE_INPUT_PATH",
)
silver_partition = parse_processing_partition(
    silver_input_path,
    "SILVER_INPUT_PATH",
)

partition_attributes = (
    "processing_date",
    "granularity",
    "reference_period",
)
if any(
    bronze_partition[attribute] != silver_partition[attribute]
    for attribute in partition_attributes
):
    raise ValueError(
        "Bronze and Silver input paths refer to different processing partitions."
    )

if silver_partition["root"].rstrip("/") != silver_root_path:
    raise ValueError(
        "SILVER_INPUT_PATH does not belong to SILVER_ROOT_PATH."
    )

partition_suffix = (
    f"processing_date={silver_partition['processing_date']}/"
    f"granularity={silver_partition['granularity']}/"
    f"reference_period={silver_partition['reference_period']}"
)
quarantine_input_path = f"{quarantine_root_path}/{partition_suffix}"

logger = configure_logger(job_name)
spark = SparkSession.builder.appName(job_name).getOrCreate()

spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.shuffle.partitions", "48")

logger.info(
    {
        "event": "dengue_batch_reconciliation_started",
        "job_name": job_name,
        "batch_id": batch_id,
        "environment": environment,
        "processing_date": silver_partition["processing_date"],
        "granularity": silver_partition["granularity"],
        "reference_period": silver_partition["reference_period"],
        "bronze_input_path": bronze_input_path,
        "silver_input_path": silver_input_path,
        "silver_root_path": silver_root_path,
        "quarantine_input_path": quarantine_input_path,
        "gold_input_path": gold_input_path,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

df_bronze = (
    spark.read.option("basePath", bronze_partition["root"])
    .parquet(bronze_input_path)
    .persist(StorageLevel.MEMORY_AND_DISK)
)
df_silver = (
    spark.read.option("basePath", silver_root_path)
    .parquet(silver_input_path)
    .persist(StorageLevel.MEMORY_AND_DISK)
)
df_silver_snapshot = spark.read.parquet(silver_root_path)
df_fact = spark.read.parquet(
    f"{gold_input_path}/fact_dengue_cases"
).persist(StorageLevel.MEMORY_AND_DISK)

dimensions = {
    "dim_date": spark.read.parquet(f"{gold_input_path}/dim_date"),
    "dim_location": spark.read.parquet(f"{gold_input_path}/dim_location"),
    "dim_disease": spark.read.parquet(f"{gold_input_path}/dim_disease"),
    "dim_demographic": spark.read.parquet(
        f"{gold_input_path}/dim_demographic"
    ),
    "dim_clinical": spark.read.parquet(f"{gold_input_path}/dim_clinical"),
}

try:
    require_columns(df_bronze, {"_batch_id"}, "Bronze")
    require_columns(
        df_silver,
        {
            "record_id",
            "record_hash",
            "source_batch_id",
            "data_quality_status",
            "silver_loaded_at",
        },
        "Silver",
    )
    require_columns(
        df_silver_snapshot,
        {
            "record_id",
            "record_hash",
            "source_batch_id",
            "data_quality_status",
            "silver_loaded_at",
            "processing_date",
        },
        "Silver snapshot",
    )
    require_columns(
        df_fact,
        {
            "case_id",
            "record_hash",
            "source_batch_id",
            "disease_key",
            "demographic_key",
            "clinical_key",
            *DATE_FOREIGN_KEYS,
            *LOCATION_FOREIGN_KEYS,
            *MEASURE_COLUMNS,
        },
        "Gold fact",
    )

    bronze_count = df_bronze.count()

    silver_stats = df_silver.agg(
        count(lit(1)).alias("silver_count"),
        spark_sum(
            when(col("data_quality_status") == "valid", 1).otherwise(0)
        ).alias("silver_valid_count"),
        spark_sum(
            when(col("data_quality_status") == "warning", 1).otherwise(0)
        ).alias("silver_warning_count"),
        spark_sum(
            when(
                ~col("data_quality_status").isin("valid", "warning"),
                1,
            ).otherwise(0)
        ).alias("silver_unexpected_status_count"),
    ).first().asDict()

    quarantine_count = 0
    quarantine_batch_mismatch_count = 0
    if path_exists(spark, quarantine_input_path):
        df_quarantine = (
            spark.read.option("basePath", quarantine_root_path)
            .option("mergeSchema", "true")
            .parquet(quarantine_input_path)
        )
        require_columns(
            df_quarantine,
            {"source_batch_id"},
            "Quarantine",
        )
        quarantine_count = df_quarantine.count()
        quarantine_batch_mismatch_count = df_quarantine.filter(
            col("source_batch_id").isNull()
            | (col("source_batch_id") != lit(batch_id))
        ).count()

    gold_count = df_fact.count()
    duplicate_case_count = duplicate_key_count(df_fact, "case_id")

    batch_identity_mismatches = {
        "bronze": df_bronze.filter(
            col("_batch_id").isNull() | (col("_batch_id") != lit(batch_id))
        ).count(),
        "silver": df_silver.filter(
            col("source_batch_id").isNull()
            | (col("source_batch_id") != lit(batch_id))
        ).count(),
        "quarantine": quarantine_batch_mismatch_count,
    }

    latest_record_window = Window.partitionBy("record_id").orderBy(
        col("silver_loaded_at").desc_nulls_last(),
        col("processing_date").desc_nulls_last(),
        col("source_batch_id").desc_nulls_last(),
    )
    df_latest_silver = (
        df_silver_snapshot.filter(
            col("data_quality_status").isin("valid", "warning")
        )
        .withColumn(
            "_reconciliation_record_version",
            row_number().over(latest_record_window),
        )
        .filter(col("_reconciliation_record_version") == 1)
        .drop("_reconciliation_record_version")
        .select(
            col("record_id").alias("case_id"),
            col("record_hash").alias("silver_record_hash"),
        )
        .persist(StorageLevel.MEMORY_AND_DISK)
    )

    silver_snapshot_count = df_latest_silver.count()
    gold_keys = df_fact.select("case_id", "record_hash")

    silver_snapshot_missing_from_gold = df_latest_silver.join(
        gold_keys.select("case_id"),
        "case_id",
        "left_anti",
    ).count()
    gold_missing_from_silver_snapshot = gold_keys.select("case_id").join(
        df_latest_silver.select("case_id"),
        "case_id",
        "left_anti",
    ).count()
    gold_record_hash_mismatch_count = (
        gold_keys.alias("gold")
        .join(df_latest_silver.alias("silver"), "case_id", "inner")
        .filter(
            ~col("gold.record_hash").eqNullSafe(
                col("silver.silver_record_hash")
            )
        )
        .count()
    )

    current_silver_gold_mismatch_count = (
        df_silver.select(
            col("record_id").alias("case_id"),
            col("record_hash").alias("silver_record_hash"),
        )
        .alias("silver")
        .join(
            gold_keys.select(
                col("case_id").alias("gold_case_id"),
                col("record_hash").alias("gold_record_hash"),
            ),
            col("silver.case_id") == col("gold_case_id"),
            "left",
        )
        .filter(
            col("gold_case_id").isNull()
            | ~col("gold_record_hash").eqNullSafe(
                col("silver.silver_record_hash")
            )
        )
        .count()
    )

    dimension_duplicate_keys = {
        "dim_date": duplicate_key_count(dimensions["dim_date"], "date_key"),
        "dim_location": duplicate_key_count(
            dimensions["dim_location"], "location_key"
        ),
        "dim_disease": duplicate_key_count(
            dimensions["dim_disease"], "disease_key"
        ),
        "dim_demographic": duplicate_key_count(
            dimensions["dim_demographic"], "demographic_key"
        ),
        "dim_clinical": duplicate_key_count(
            dimensions["dim_clinical"], "clinical_key"
        ),
    }

    orphan_foreign_keys = {
        key: orphan_key_count(
            df_fact,
            dimensions["dim_date"],
            key,
            "date_key",
        )
        for key in DATE_FOREIGN_KEYS
    }
    orphan_foreign_keys.update(
        {
            key: orphan_key_count(
                df_fact,
                dimensions["dim_location"],
                key,
                "location_key",
            )
            for key in LOCATION_FOREIGN_KEYS
        }
    )
    orphan_foreign_keys.update(
        {
            "disease_key": orphan_key_count(
                df_fact,
                dimensions["dim_disease"],
                "disease_key",
                "disease_key",
            ),
            "demographic_key": orphan_key_count(
                df_fact,
                dimensions["dim_demographic"],
                "demographic_key",
                "demographic_key",
            ),
            "clinical_key": orphan_key_count(
                df_fact,
                dimensions["dim_clinical"],
                "clinical_key",
                "clinical_key",
            ),
        }
    )

    invalid_measure_condition = (
        col("notification_count").isNull()
        | (col("notification_count") != lit(1))
    )
    for measure_column in MEASURE_COLUMNS:
        if measure_column != "notification_count":
            invalid_measure_condition = invalid_measure_condition | (
                col(measure_column).isNull()
                | ~col(measure_column).isin(0, 1)
            )

    invalid_measure_count = df_fact.filter(
        invalid_measure_condition
    ).count()

    silver_count = int(silver_stats["silver_count"] or 0)
    silver_valid_count = int(silver_stats["silver_valid_count"] or 0)
    silver_warning_count = int(silver_stats["silver_warning_count"] or 0)
    silver_unexpected_status_count = int(
        silver_stats["silver_unexpected_status_count"] or 0
    )

    checks = {
        "bronze_equals_silver_plus_quarantine": (
            bronze_count == silver_count + quarantine_count
        ),
        "silver_status_totals_close": (
            silver_count == silver_valid_count + silver_warning_count
            and silver_unexpected_status_count == 0
        ),
        "gold_equals_latest_silver_snapshot": (
            gold_count == silver_snapshot_count
        ),
        "gold_case_set_matches_silver_snapshot": (
            silver_snapshot_missing_from_gold == 0
            and gold_missing_from_silver_snapshot == 0
        ),
        "gold_record_hashes_match_silver_snapshot": (
            gold_record_hash_mismatch_count == 0
        ),
        "current_silver_batch_is_published_in_gold": (
            current_silver_gold_mismatch_count == 0
        ),
        "fact_grain_is_unique": duplicate_case_count == 0,
        "batch_identity_is_consistent": all(
            value == 0 for value in batch_identity_mismatches.values()
        ),
        "dimension_keys_are_unique": all(
            value == 0 for value in dimension_duplicate_keys.values()
        ),
        "foreign_keys_are_valid": all(
            value == 0 for value in orphan_foreign_keys.values()
        ),
        "fact_measures_are_binary": invalid_measure_count == 0,
    }

    reconciliation_status = (
        "SUCCEEDED" if all(checks.values()) else "FAILED"
    )

    report = {
        "batch_id": batch_id,
        "environment": environment,
        "status": reconciliation_status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "bronze": bronze_count,
            "silver": silver_count,
            "silver_valid": silver_valid_count,
            "silver_warning": silver_warning_count,
            "silver_unexpected_status": silver_unexpected_status_count,
            "quarantine": quarantine_count,
            "silver_snapshot_latest_records": silver_snapshot_count,
            "gold_fact": gold_count,
            "duplicate_cases": duplicate_case_count,
            "invalid_measure_rows": invalid_measure_count,
            "silver_snapshot_missing_from_gold": (
                silver_snapshot_missing_from_gold
            ),
            "gold_missing_from_silver_snapshot": (
                gold_missing_from_silver_snapshot
            ),
            "gold_record_hash_mismatches": (
                gold_record_hash_mismatch_count
            ),
            "current_silver_gold_mismatches": (
                current_silver_gold_mismatch_count
            ),
        },
        "batch_identity_mismatches": batch_identity_mismatches,
        "dimension_duplicate_keys": dimension_duplicate_keys,
        "orphan_foreign_keys": orphan_foreign_keys,
        "checks": checks,
        "paths": {
            "bronze": bronze_input_path,
            "silver": silver_input_path,
            "quarantine": quarantine_input_path,
            "silver_root": silver_root_path,
            "gold": gold_input_path,
        },
    }

    report_path = write_json_report(
        reconciliation_output_path,
        batch_id,
        report,
    )

    logger.info(
        {
            "event": "dengue_batch_reconciliation_finished",
            "job_name": job_name,
            "batch_id": batch_id,
            "status": reconciliation_status,
            "report_path": report_path,
            "counts": report["counts"],
            "checks": checks,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    if reconciliation_status == "FAILED" and fail_on_mismatch:
        failed_checks = sorted(
            name for name, passed in checks.items() if not passed
        )
        raise ValueError(
            "Dengue batch reconciliation failed: "
            + ", ".join(failed_checks)
        )
finally:
    df_bronze.unpersist()
    df_silver.unpersist()
    if "df_latest_silver" in locals():
        df_latest_silver.unpersist()
    df_fact.unpersist()
