data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  data_lake_bucket_name      = "${var.project_name}-${var.environment}-data-lake-${local.account_id}"
  artifacts_bucket_name      = "${var.project_name}-${var.environment}-artifacts-${local.account_id}"
  athena_results_bucket_name = "${var.project_name}-${var.environment}-athena-results-${local.account_id}"
  logs_bucket_name           = "${var.project_name}-${var.environment}-logs-${local.account_id}"

  bronze_database_name    = "${var.project_name}_${var.environment}_bronze"
  silver_database_name    = "${var.project_name}_${var.environment}_silver"
  gold_database_name      = "${var.project_name}_${var.environment}_gold"
  warehouse_database_name = "${var.project_name}_${var.environment}_warehouse"

  glue_execution_role_name = "${var.project_name}-${var.environment}-glue-execution-role"
  glue_s3_policy_name      = "${var.project_name}-${var.environment}-glue-s3-access-policy"

  athena_workgroup_name = "${var.project_name}-${var.environment}-workgroup"

  bronze_ingestion_job_name    = "${var.project_name}-${var.environment}-bronze-ingestion"
  bronze_ingestion_script_key  = "glue/scripts/bronze_ingestion/bronze_ingestion.py"
  bronze_ingestion_script_path = "${path.root}/../../../../src/glue/jobs/bronze_ingestion/bronze_ingestion.py"

  silver_arbovirus_cases_job_name    = "${var.project_name}-${var.environment}-silver-arbovirus-cases"
  silver_arbovirus_cases_script_key  = "glue/scripts/silver_arbovirus_cases/silver_arbovirus_cases.py"
  silver_arbovirus_cases_script_path = "${path.root}/../../../../src/glue/jobs/silver_arbovirus_cases/silver_arbovirus_cases.py"

  gold_arbovirus_job_name     = "${var.project_name}-${var.environment}-gold-arbovirus-star-schema"
  gold_arbovirus_script_key   = "glue/scripts/gold_arbovirus_star_schema/gold_arbovirus_star_schema.py"
  gold_arbovirus_script_path  = "${path.root}/../../../../src/glue/jobs/gold_arbovirus_star_schema/gold_arbovirus_star_schema.py"
  gold_arbovirus_crawler_name = "${var.project_name}-${var.environment}-gold-arbovirus"

  bronze_staging_input_path = "s3://${module.data_lake_bucket.bucket_name}/staging/opendatasus/arboviroses/"
  bronze_output_path        = "s3://${module.data_lake_bucket.bucket_name}/bronze/opendatasus/arboviroses/"

  ibge_municipalities_reference_path = "s3://${module.data_lake_bucket.bucket_name}/reference/ibge/municipalities/municipios_ufs_ibge.json"
  silver_arbovirus_cases_output_path = "s3://${module.data_lake_bucket.bucket_name}/silver/opendatasus/arboviroses/"
  silver_arbovirus_quarantine_path   = "s3://${module.data_lake_bucket.bucket_name}/quarantine/opendatasus/arboviroses/silver_cases/"
  gold_arbovirus_output_path         = "s3://${module.data_lake_bucket.bucket_name}/gold/opendatasus/arboviroses/"
}

module "data_lake_bucket" {
  source = "../../modules/s3"

  bucket_name   = local.data_lake_bucket_name
  force_destroy = true

  prefixes = [
    "staging/",
    "bronze/",
    "silver/",
    "gold/",
    "warehouse/",
    "quarantine/",
    "reference/"
  ]

  tags = {
    purpose = "data-lake"
  }
}

module "artifacts_bucket" {
  source = "../../modules/s3"

  bucket_name   = local.artifacts_bucket_name
  force_destroy = true

  prefixes = [
    "glue/scripts/",
    "lambda/packages/",
    "dependencies/"
  ]

  tags = {
    purpose = "artifacts"
  }
}

module "athena_results_bucket" {
  source = "../../modules/s3"

  bucket_name   = local.athena_results_bucket_name
  force_destroy = true

  prefixes = [
    "query-results/"
  ]

  tags = {
    purpose = "athena-results"
  }
}

module "logs_bucket" {
  source = "../../modules/s3"

  bucket_name   = local.logs_bucket_name
  force_destroy = true

  prefixes = [
    "cloudwatch/",
    "pipeline-runs/"
  ]

  tags = {
    purpose = "logs"
  }
}

module "glue_catalog" {
  source = "../../modules/glue_catalog"

  databases = {
    (local.bronze_database_name) = {
      description = "Glue Catalog database for raw data stored in the Bronze layer."
    }

    (local.silver_database_name) = {
      description = "Glue Catalog database for curated and standardized data stored in the Silver layer."
    }

    (local.gold_database_name) = {
      description = "Glue Catalog database for analytical datasets and indicators stored in the Gold layer."
    }

    (local.warehouse_database_name) = {
      description = "Glue Catalog database for dimensional Data Warehouse tables."
    }
  }

  default_parameters = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}

module "athena" {
  source = "../../modules/athena"

  workgroup_name      = local.athena_workgroup_name
  results_bucket_name = module.athena_results_bucket.bucket_name
  results_prefix      = "query-results/"

  bytes_scanned_cutoff_per_query = 1073741824

  tags = {
    purpose = "query-engine"
  }
}

module "iam_glue_role" {
  source = "../../modules/iam_glue_role"

  role_name   = local.glue_execution_role_name
  policy_name = local.glue_s3_policy_name

  data_lake_bucket_arn = module.data_lake_bucket.bucket_arn
  artifacts_bucket_arn = module.artifacts_bucket.bucket_arn
  logs_bucket_arn      = module.logs_bucket.bucket_arn

  tags = {
    purpose = "glue-execution"
  }
}

resource "aws_s3_object" "bronze_ingestion_script" {
  bucket = module.artifacts_bucket.bucket_name
  key    = local.bronze_ingestion_script_key
  source = local.bronze_ingestion_script_path

  source_hash = filemd5(local.bronze_ingestion_script_path)

  tags = {
    purpose = "glue-script"
  }
}

module "bronze_ingestion_glue_job" {
  source = "../../modules/glue_job"

  job_name        = local.bronze_ingestion_job_name
  role_arn        = module.iam_glue_role.role_arn
  script_location = "s3://${module.artifacts_bucket.bucket_name}/${aws_s3_object.bronze_ingestion_script.key}"

  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 10
  max_retries       = 0

  default_arguments = {
    "--ENVIRONMENT"           = var.environment
    "--STAGING_INPUT_PATH"    = local.bronze_staging_input_path
    "--BRONZE_OUTPUT_PATH"    = local.bronze_output_path
    "--PARTITION_DATE_COLUMN" = "dt_notific"
    "--WRITE_MODE"            = "overwrite"
  }

  tags = {
    purpose = "bronze-ingestion"
    layer   = "bronze"
  }
}

resource "aws_s3_object" "silver_arbovirus_cases_script" {
  bucket = module.artifacts_bucket.bucket_name
  key    = local.silver_arbovirus_cases_script_key
  source = local.silver_arbovirus_cases_script_path

  source_hash = filemd5(local.silver_arbovirus_cases_script_path)

  tags = {
    purpose = "glue-script"
  }
}

module "silver_arbovirus_cases_glue_job" {
  source = "../../modules/glue_job"

  job_name        = local.silver_arbovirus_cases_job_name
  role_arn        = module.iam_glue_role.role_arn
  script_location = "s3://${module.artifacts_bucket.bucket_name}/${aws_s3_object.silver_arbovirus_cases_script.key}"

  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 15
  max_retries       = 0

  default_arguments = {
    "--ENVIRONMENT"            = var.environment
    "--BRONZE_INPUT_PATH"      = local.bronze_output_path
    "--IBGE_REFERENCE_PATH"    = local.ibge_municipalities_reference_path
    "--SILVER_OUTPUT_PATH"     = local.silver_arbovirus_cases_output_path
    "--QUARANTINE_OUTPUT_PATH" = local.silver_arbovirus_quarantine_path
    "--WRITE_MODE"             = "overwrite"
  }

  tags = {
    purpose = "silver-arbovirus-cases"
    layer   = "silver"
  }
}

resource "aws_s3_object" "gold_arbovirus_script" {
  bucket = module.artifacts_bucket.bucket_name
  key    = local.gold_arbovirus_script_key
  source = local.gold_arbovirus_script_path

  source_hash = filemd5(local.gold_arbovirus_script_path)

  tags = {
    purpose = "glue-script"
  }
}

module "gold_arbovirus_glue_job" {
  source = "../../modules/glue_job"

  job_name        = local.gold_arbovirus_job_name
  role_arn        = module.iam_glue_role.role_arn
  script_location = "s3://${module.artifacts_bucket.bucket_name}/${aws_s3_object.gold_arbovirus_script.key}"

  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 15
  max_retries       = 0

  default_arguments = {
    "--ENVIRONMENT"       = var.environment
    "--SILVER_INPUT_PATH" = local.silver_arbovirus_cases_output_path
    "--GOLD_OUTPUT_PATH"  = local.gold_arbovirus_output_path
    "--WRITE_MODE"        = "overwrite"
  }

  tags = {
    purpose = "gold-arbovirus-star-schema"
    layer   = "gold"
  }
}

resource "aws_glue_crawler" "gold_arbovirus" {
  name          = local.gold_arbovirus_crawler_name
  database_name = local.gold_database_name
  role          = module.iam_glue_role.role_arn
  table_prefix  = "arbovirus_"

  s3_target {
    path = local.gold_arbovirus_output_path
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable"
      }
      Tables = {
        AddOrUpdateBehavior = "MergeNewColumns"
      }
    }
  })

  depends_on = [module.glue_catalog]

  tags = {
    purpose = "gold-arbovirus-catalog"
    layer   = "gold"
  }
}
