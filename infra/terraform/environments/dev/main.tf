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
}

module "data_lake_bucket" {
  source = "../../modules/s3"

  bucket_name   = local.data_lake_bucket_name
  force_destroy = true

  prefixes = [
    "bronze/",
    "silver/",
    "gold/",
    "warehouse/",
    "quarantine/"
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