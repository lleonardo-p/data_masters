data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  data_lake_bucket_name      = "${var.project_name}-${var.environment}-data-lake-${local.account_id}"
  artifacts_bucket_name      = "${var.project_name}-${var.environment}-artifacts-${local.account_id}"
  athena_results_bucket_name = "${var.project_name}-${var.environment}-athena-results-${local.account_id}"
  logs_bucket_name           = "${var.project_name}-${var.environment}-logs-${local.account_id}"
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