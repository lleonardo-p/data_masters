import logging
import re
import sys
import time
import unicodedata
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
    regexp_extract,
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

spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.parquet.compression.codec", "snappy")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
spark.conf.set("spark.sql.shuffle.partitions", "48")

logger.info(
    {
        "event": "bronze_ingestion_started",
        "job_name": job_name,
        "batch_id": batch_id,
        "environment": environment,
        "staging_input_path": staging_input_path,
        "bronze_output_path": bronze_output_path,
        "source_column_count": len(SOURCE_COLUMNS),
        "write_mode": write_mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

source_schema = StructType(
    [StructField(column_name, StringType(), True) for column_name in SOURCE_COLUMNS]
)

# recursiveFileLookup permite ler todos os anos abaixo da raiz da Staging.
# FAILFAST impede que uma mudanca estrutural da fonte seja ignorada em silencio.
df_raw = (
    spark.read
    .option("header", "true")
    .option("sep", ",")
    .option("quote", '"')
    .option("escape", '"')
    .option("encoding", "UTF-8")
    .option("dateFormat", "yyyy-MM-dd")
    .option("mode", "FAILFAST")
    .option("enforceSchema", "false")
    .option("recursiveFileLookup", "true")
    .option("pathGlobFilter", "*.csv")
    .schema(source_schema)
    .csv(staging_input_path)
)

if not df_raw.columns:
    raise ValueError(f"No columns found in input path: {staging_input_path}")

df = df_raw.select(
    [
        col(original).alias(normalize_column_name(original))
        for original in SOURCE_COLUMNS
    ]
)

df = df.withColumn("_source_file", input_file_name())

# reference_year vem do path da Staging e representa o arquivo oficial anual.
df = df.withColumn(
    "reference_year",
    when(
        regexp_extract(
            col("_source_file"),
            r"reference_year=([0-9]{4})",
            1,
        )
        != "",
        regexp_extract(
            col("_source_file"),
            r"reference_year=([0-9]{4})",
            1,
        ),
    ).otherwise(lit("unknown")),
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
    .withColumn("_source_format", lit("csv"))
    .withColumn("_bronze_loaded_at", current_timestamp())
    .withColumn("_environment", lit(environment))
)

# O cache evita uma segunda leitura completa dos CSVs entre metricas e escrita.
df = df.persist(StorageLevel.MEMORY_AND_DISK)

try:
    ingestion_stats = (
        df.agg(
            count(lit(1)).alias("record_count"),
            coalesce(
                spark_sum(
                    when(col("reference_year") == "unknown", 1).otherwise(0)
                ),
                lit(0),
            ).alias("unknown_reference_year_count"),
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

    logger.info(
        {
            "event": "bronze_ingestion_statistics",
            "job_name": job_name,
            "batch_id": batch_id,
            **ingestion_stats,
        }
    )

    (
        df.repartition(
            "disease",
            "reference_year",
            "notification_year",
            "notification_month",
        )
        .write
        .mode(write_mode)
        .option("compression", "snappy")
        .partitionBy(
            "disease",
            "reference_year",
            "notification_year",
            "notification_month",
        )
        .parquet(bronze_output_path)
    )

    logger.info(
        {
            "event": "bronze_ingestion_finished",
            "job_name": job_name,
            "batch_id": batch_id,
            **ingestion_stats,
            "bronze_output_path": bronze_output_path,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    )
finally:
    df.unpersist()
