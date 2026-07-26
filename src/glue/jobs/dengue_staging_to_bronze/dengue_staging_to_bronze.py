import json
import logging
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse

import boto3
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
    sum as spark_sum,
    to_date,
    trim,
    upper,
    when,
)
from pyspark.sql.types import StringType, StructField, StructType


# Contrato estrutural comum aos arquivos DENGBR24, DENGBR25 e DENGBR26.
# Todos os campos de origem permanecem como string na Bronze. A conversao
# semantica de tipos e as regras de qualidade pertencem a Silver.
SOURCE_COLUMNS = [
    "TP_NOT",
    "ID_AGRAVO",
    "DT_NOTIFIC",
    "SEM_NOT",
    "NU_ANO",
    "SG_UF_NOT",
    "ID_MUNICIP",
    "ID_REGIONA",
    "ID_UNIDADE",
    "DT_SIN_PRI",
    "SEM_PRI",
    "ANO_NASC",
    "NU_IDADE_N",
    "CS_SEXO",
    "CS_GESTANT",
    "CS_RACA",
    "CS_ESCOL_N",
    "SG_UF",
    "ID_MN_RESI",
    "ID_RG_RESI",
    "ID_PAIS",
    "DT_INVEST",
    "ID_OCUPA_N",
    "FEBRE",
    "MIALGIA",
    "CEFALEIA",
    "EXANTEMA",
    "VOMITO",
    "NAUSEA",
    "DOR_COSTAS",
    "CONJUNTVIT",
    "ARTRITE",
    "ARTRALGIA",
    "PETEQUIA_N",
    "LEUCOPENIA",
    "LACO",
    "DOR_RETRO",
    "DIABETES",
    "HEMATOLOG",
    "HEPATOPAT",
    "RENAL",
    "HIPERTENSA",
    "ACIDO_PEPT",
    "AUTO_IMUNE",
    "DT_CHIK_S1",
    "DT_CHIK_S2",
    "DT_PRNT",
    "RES_CHIKS1",
    "RES_CHIKS2",
    "RESUL_PRNT",
    "DT_SORO",
    "RESUL_SORO",
    "DT_NS1",
    "RESUL_NS1",
    "DT_VIRAL",
    "RESUL_VI_N",
    "DT_PCR",
    "RESUL_PCR_",
    "SOROTIPO",
    "HISTOPA_N",
    "IMUNOH_N",
    "HOSPITALIZ",
    "DT_INTERNA",
    "UF",
    "MUNICIPIO",
    "TPAUTOCTO",
    "COUFINF",
    "COPAISINF",
    "COMUNINF",
    "CLASSI_FIN",
    "CRITERIO",
    "DOENCA_TRA",
    "CLINC_CHIK",
    "EVOLUCAO",
    "DT_OBITO",
    "DT_ENCERRA",
    "ALRM_HIPOT",
    "ALRM_PLAQ",
    "ALRM_VOM",
    "ALRM_SANG",
    "ALRM_HEMAT",
    "ALRM_ABDOM",
    "ALRM_LETAR",
    "ALRM_HEPAT",
    "ALRM_LIQ",
    "DT_ALRM",
    "GRAV_PULSO",
    "GRAV_CONV",
    "GRAV_ENCH",
    "GRAV_INSUF",
    "GRAV_TAQUI",
    "GRAV_EXTRE",
    "GRAV_HIPOT",
    "GRAV_HEMAT",
    "GRAV_MELEN",
    "GRAV_METRO",
    "GRAV_SANG",
    "GRAV_AST",
    "GRAV_MIOC",
    "GRAV_CONSC",
    "GRAV_ORGAO",
    "DT_GRAV",
    "MANI_HEMOR",
    "EPISTAXE",
    "GENGIVO",
    "METRO",
    "PETEQUIAS",
    "HEMATURA",
    "SANGRAM",
    "LACO_N",
    "PLASMATICO",
    "EVIDENCIA",
    "PLAQ_MENOR",
    "CON_FHD",
    "COMPLICA",
    "TP_SISTEMA",
    "NDUPLIC_N",
    "DT_DIGITA",
    "CS_FLXRET",
    "FLXRECEBI",
    "MIGRADO_W",
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


def normalize_column_name(column_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", column_name)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.strip().lower()
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_") or "unknown_column"


def parse_staging_input_path(staging_input_path: str) -> dict[str, str]:
    normalized_path = staging_input_path.rstrip("/")
    parsed = urlparse(normalized_path)

    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(
            "STAGING_INPUT_PATH must be a valid S3 URI."
        )

    if not parsed.path.endswith("/dengue.jsonl.gz"):
        raise ValueError(
            "STAGING_INPUT_PATH must point to dengue.jsonl.gz."
        )

    match = re.search(
        r"/processing_date=(?P<processing_date>[0-9]{4}-[0-9]{2}-[0-9]{2})"
        r"/granularity=(?P<granularity>day|month)"
        r"/reference_period=(?P<reference_period>[0-9]{4}-(?:[0-9]{2}|[0-9]{2}-[0-9]{2}))"
        r"/dengue\.jsonl\.gz$",
        parsed.path,
    )

    if match is None:
        raise ValueError(
            "STAGING_INPUT_PATH does not follow the expected partition layout."
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

    data_key = parsed.path.lstrip("/")
    manifest_key = (
        f"{data_key.rsplit('/', 1)[0]}/manifest.json"
    )

    return {
        **metadata,
        "bucket": parsed.netloc,
        "data_key": data_key,
        "manifest_key": manifest_key,
        "manifest_uri": f"s3://{parsed.netloc}/{manifest_key}",
        "reference_year": reference_period[:4],
    }


def load_source_manifest(
    bucket: str,
    manifest_key: str,
) -> dict:
    response = boto3.client("s3").get_object(
        Bucket=bucket,
        Key=manifest_key,
    )
    manifest = json.loads(
        response["Body"].read().decode("utf-8")
    )

    required_fields = {
        "status",
        "batch_id",
        "granularity",
        "reference_period",
        "processing_date",
        "record_count",
        "compressed_sha256",
        "s3_bucket",
        "s3_key",
        "completed_at",
    }
    missing_fields = sorted(
        required_fields.difference(manifest)
    )

    if missing_fields:
        raise ValueError(
            "Missing source manifest fields: "
            f"{', '.join(missing_fields)}"
        )

    if manifest["status"] != "SUCCEEDED":
        raise ValueError(
            "Source manifest status must be SUCCEEDED."
        )

    return manifest


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "BATCH_ID",
        "ENVIRONMENT",
        "STAGING_INPUT_PATH",
        "BRONZE_OUTPUT_PATH",
        "WRITE_MODE",
    ],
)

job_name = args["JOB_NAME"]
batch_id = args["BATCH_ID"]
environment = args["ENVIRONMENT"]
staging_input_path = args["STAGING_INPUT_PATH"]
bronze_output_path = args["BRONZE_OUTPUT_PATH"]
write_mode = args["WRITE_MODE"].lower()

if write_mode not in {"append", "overwrite"}:
    raise ValueError(
        f"Invalid WRITE_MODE: {write_mode}. Expected append or overwrite."
    )

logger = configure_logger(job_name)
spark = SparkSession.builder.appName(job_name).getOrCreate()
staging_metadata = parse_staging_input_path(staging_input_path)
source_manifest = load_source_manifest(
    staging_metadata["bucket"],
    staging_metadata["manifest_key"],
)

manifest_contract = {
    "s3_bucket": staging_metadata["bucket"],
    "s3_key": staging_metadata["data_key"],
    "processing_date": staging_metadata["processing_date"],
    "granularity": staging_metadata["granularity"],
    "reference_period": staging_metadata["reference_period"],
}
manifest_mismatches = {
    key: {
        "expected": expected_value,
        "actual": source_manifest.get(key),
    }
    for key, expected_value in manifest_contract.items()
    if str(source_manifest.get(key)) != expected_value
}

if manifest_mismatches:
    raise ValueError(
        "Source manifest does not match STAGING_INPUT_PATH: "
        f"{json.dumps(manifest_mismatches, sort_keys=True)}"
    )

spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.parquet.compression.codec", "snappy")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
spark.conf.set("spark.sql.shuffle.partitions", "48")

logger.info(
    {
        "event": "dengue_staging_to_bronze_started",
        "job_name": job_name,
        "batch_id": batch_id,
        "environment": environment,
        "staging_input_path": staging_input_path,
        "bronze_output_path": bronze_output_path,
        "source_manifest_path": staging_metadata["manifest_uri"],
        "processing_date": staging_metadata["processing_date"],
        "granularity": staging_metadata["granularity"],
        "reference_period": staging_metadata["reference_period"],
        "source_column_count": len(SOURCE_COLUMNS),
        "write_mode": write_mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

source_schema = StructType([
    StructField(column_name, StringType(), True)
    for column_name in SOURCE_COLUMNS
])

# O Spark descompacta .gz automaticamente. A entrada é um único JSON por linha,
# com schema explícito para preservar todas as colunas de origem como string.
df_raw = (
    spark.read
    .option("mode", "FAILFAST")
    .option("multiLine", "false")
    .schema(source_schema)
    .json(staging_input_path)
)

if not df_raw.columns:
    raise ValueError(f"No columns found in input path: {staging_input_path}")

df = df_raw.select(
    [
        col(original).alias(normalize_column_name(original))
        for original in SOURCE_COLUMNS
    ]
)

df = (
    df.withColumn("_source_file", input_file_name())
    .withColumn(
        "processing_date",
        lit(staging_metadata["processing_date"]),
    )
    .withColumn(
        "granularity",
        lit(staging_metadata["granularity"]),
    )
    .withColumn(
        "reference_period",
        lit(staging_metadata["reference_period"]),
    )
    .withColumn(
        "reference_year",
        lit(staging_metadata["reference_year"]),
    )
)

df = df.withColumn(
    "_notification_date",
    to_date(trim(col("dt_notific")), "yyyy-MM-dd"),
)

df = (
    df.withColumn(
        "notification_year",
        when(
            col("_notification_date").isNotNull(),
            date_format(col("_notification_date"), "yyyy"),
        ).otherwise(lit("unknown")),
    )
    .withColumn(
        "notification_month",
        when(
            col("_notification_date").isNotNull(),
            date_format(col("_notification_date"), "MM"),
        ).otherwise(lit("unknown")),
    )
)

df = df.withColumn(
    "disease",
    when(upper(trim(col("id_agravo"))) == "A90", lit("dengue")).otherwise(
        lit("unknown")
    ),
)

df = (
    df.withColumn("_batch_id", lit(batch_id))
    .withColumn("_source_system", lit("opendatasus_sinan"))
    .withColumn("_ingestion_source", lit("dengue_source_api"))
    .withColumn("_source_format", lit("jsonl.gz"))
    .withColumn(
        "_source_extraction_batch_id",
        lit(str(source_manifest["batch_id"])),
    )
    .withColumn(
        "_source_manifest",
        lit(staging_metadata["manifest_uri"]),
    )
    .withColumn("_bronze_loaded_at", current_timestamp())
    .withColumn("_environment", lit(environment))
)

# O cache evita uma segunda leitura completa do JSONL.Gzip entre métricas e escrita.
df = df.persist(StorageLevel.MEMORY_AND_DISK)

try:
    ingestion_stats = (
        df.agg(
            count(lit(1)).alias("record_count"),
            coalesce(
                spark_sum(
                    when(col("_notification_date").isNull(), 1).otherwise(0)
                ),
                lit(0),
            ).alias("invalid_notification_date_count"),
            coalesce(
                spark_sum(
                    when(col("disease") == "unknown", 1).otherwise(0)
                ),
                lit(0),
            ).alias("unknown_disease_count"),
        )
        .first()
        .asDict()
    )

    expected_record_count = int(source_manifest["record_count"])

    if ingestion_stats["record_count"] != expected_record_count:
        raise ValueError(
            "Bronze record count does not match source manifest: "
            f"expected={expected_record_count}, "
            f"actual={ingestion_stats['record_count']}."
        )

    logger.info(
        {
            "event": "dengue_staging_to_bronze_statistics",
            "job_name": job_name,
            "batch_id": batch_id,
            "source_extraction_batch_id": source_manifest["batch_id"],
            "source_compressed_sha256": source_manifest[
                "compressed_sha256"
            ],
            **ingestion_stats,
        }
    )

    (
        df.repartition(
            "processing_date",
            "granularity",
            "reference_period",
        )
        .write
        .mode(write_mode)
        .option("compression", "snappy")
        .partitionBy(
            "processing_date",
            "granularity",
            "reference_period",
        )
        .parquet(bronze_output_path)
    )

    logger.info(
        {
            "event": "dengue_staging_to_bronze_finished",
            "job_name": job_name,
            "batch_id": batch_id,
            "processing_date": staging_metadata["processing_date"],
            "granularity": staging_metadata["granularity"],
            "reference_period": staging_metadata["reference_period"],
            **ingestion_stats,
            "bronze_output_path": bronze_output_path,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )
finally:
    df.unpersist()
