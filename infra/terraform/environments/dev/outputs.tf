output "data_lake_bucket_name" {
  description = "Main BAIP Data Lake bucket."
  value       = module.data_lake_bucket.bucket_name
}

output "artifacts_bucket_name" {
  description = "Bucket used to store Glue scripts, Lambda packages and dependencies."
  value       = module.artifacts_bucket.bucket_name
}

output "athena_results_bucket_name" {
  description = "Bucket used to store Athena query results."
  value       = module.athena_results_bucket.bucket_name
}

output "logs_bucket_name" {
  description = "Bucket used to store logs and operational evidences."
  value       = module.logs_bucket.bucket_name
}

output "glue_database_names" {
  description = "Glue Catalog databases created for BAIP."
  value       = module.glue_catalog.database_names
}

output "athena_workgroup_name" {
  description = "Athena workgroup used for BAIP analytical queries."
  value       = module.athena.workgroup_name
}

output "glue_execution_role_name" {
  description = "IAM role name used by AWS Glue jobs."
  value       = module.iam_glue_role.role_name
}

output "glue_execution_role_arn" {
  description = "IAM role ARN used by AWS Glue jobs."
  value       = module.iam_glue_role.role_arn
}

output "bronze_ingestion_glue_job_name" {
  description = "Bronze ingestion AWS Glue job name."
  value       = module.bronze_ingestion_glue_job.job_name
}

output "bronze_ingestion_glue_job_arn" {
  description = "Bronze ingestion AWS Glue job ARN."
  value       = module.bronze_ingestion_glue_job.job_arn
}