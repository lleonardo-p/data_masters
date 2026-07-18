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
    sum as spark_sum,
    when,
)


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
        "QUARANTINE_INPUT_PATH",
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
quarantine_input_path = args["QUARANTINE_INPUT_PATH"].rstrip("/")
gold_input_path = args["GOLD_INPUT_PATH"].rstrip("/")
reconciliation_output_path = args["RECONCILIATION_OUTPUT_PATH"].rstrip("/")
fail_on_mismatch = args["FAIL_ON_MISMATCH"].lower() == "true"

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
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

df_bronze = spark.read.parquet(bronze_input_path).persist(
    StorageLevel.MEMORY_AND_DISK
)
df_silver = spark.read.parquet(silver_input_path).persist(
    StorageLevel.MEMORY_AND_DISK
)
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
        {"record_id", "source_batch_id", "data_quality_status"},
        "Silver",
    )
    require_columns(
        df_fact,
        {
            "case_id",
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
    quarantine_other_batch_count = 0
    quarantine_legacy_count = 0
    if path_exists(spark, quarantine_input_path):
        df_quarantine = (
            spark.read.option("mergeSchema", "true")
            .parquet(quarantine_input_path)
        )

        if "source_batch_id" in df_quarantine.columns:
            quarantine_stats = df_quarantine.agg(
                spark_sum(
                    when(col("source_batch_id") == lit(batch_id), 1)
                    .otherwise(0)
                ).alias("current_batch_count"),
                spark_sum(
                    when(
                        col("source_batch_id").isNotNull()
                        & (col("source_batch_id") != lit(batch_id)),
                        1,
                    ).otherwise(0)
                ).alias("other_batch_count"),
                spark_sum(
                    when(col("source_batch_id").isNull(), 1).otherwise(0)
                ).alias("legacy_count"),
            ).first().asDict()

            quarantine_count = int(
                quarantine_stats["current_batch_count"] or 0
            )
            quarantine_other_batch_count = int(
                quarantine_stats["other_batch_count"] or 0
            )
            quarantine_legacy_count = int(
                quarantine_stats["legacy_count"] or 0
            )
        else:
            quarantine_legacy_count = df_quarantine.count()

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
        "gold": df_fact.filter(
            col("source_batch_id").isNull()
            | (col("source_batch_id") != lit(batch_id))
        ).count(),
    }

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
        "gold_equals_silver": gold_count == silver_count,
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
            "quarantine_other_batches": quarantine_other_batch_count,
            "quarantine_legacy_without_batch_id": quarantine_legacy_count,
            "gold_fact": gold_count,
            "duplicate_cases": duplicate_case_count,
            "invalid_measure_rows": invalid_measure_count,
        },
        "batch_identity_mismatches": batch_identity_mismatches,
        "dimension_duplicate_keys": dimension_duplicate_keys,
        "orphan_foreign_keys": orphan_foreign_keys,
        "checks": checks,
        "paths": {
            "bronze": bronze_input_path,
            "silver": silver_input_path,
            "quarantine": quarantine_input_path,
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
    df_fact.unpersist()
