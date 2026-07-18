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
  description = "Bronze dengue ingestion AWS Glue job name."
  value       = module.bronze_ingestion_glue_job.job_name
}

output "bronze_ingestion_glue_job_arn" {
  description = "Bronze dengue ingestion AWS Glue job ARN."
  value       = module.bronze_ingestion_glue_job.job_arn
}

output "ibge_municipalities_reference_path" {
  description = "S3 path used by Glue for the IBGE municipalities reference."
  value       = local.ibge_municipalities_reference_path
}

output "bronze_dengue_staging_input_path" {
  description = "S3 input path containing the official dengue CSV files."
  value       = local.bronze_dengue_staging_input_path
}

output "bronze_dengue_output_path" {
  description = "S3 output path for dengue Bronze data."
  value       = local.bronze_dengue_output_path
}

output "silver_dengue_cases_output_path" {
  description = "S3 output path for curated dengue cases."
  value       = local.silver_dengue_cases_output_path
}

output "silver_dengue_quarantine_path" {
  description = "S3 quarantine path for invalid Silver dengue records."
  value       = local.silver_dengue_quarantine_path
}

output "silver_dengue_cases_glue_job_name" {
  description = "Silver dengue cases AWS Glue job name."
  value       = module.silver_dengue_cases_glue_job.job_name
}

output "silver_dengue_cases_glue_job_arn" {
  description = "Silver dengue cases AWS Glue job ARN."
  value       = module.silver_dengue_cases_glue_job.job_arn
}

output "gold_dengue_output_path" {
  description = "S3 root path for the dengue dimensional model."
  value       = local.gold_dengue_output_path
}

output "gold_dengue_glue_job_name" {
  description = "Gold dengue star schema AWS Glue job name."
  value       = module.gold_dengue_glue_job.job_name
}

output "gold_dengue_glue_job_arn" {
  description = "Gold dengue star schema AWS Glue job ARN."
  value       = module.gold_dengue_glue_job.job_arn
}

output "gold_dengue_crawler_name" {
  description = "Glue crawler that registers Gold dengue tables."
  value       = aws_glue_crawler.gold_dengue.name
}

output "dengue_batch_reconciliation_glue_job_name" {
  description = "Glue job that reconciles Bronze, Silver, quarantine and Gold."
  value       = module.dengue_batch_reconciliation_glue_job.job_name
}

output "dengue_batch_reconciliation_output_path" {
  description = "S3 path containing dengue batch reconciliation manifests."
  value       = local.dengue_batch_reconciliation_output_path
}

output "dengue_batch_state_machine_name" {
  description = "Step Functions state machine for the complete dengue batch."
  value       = aws_sfn_state_machine.dengue_batch.name
}

output "dengue_batch_state_machine_arn" {
  description = "ARN of the complete dengue batch state machine."
  value       = aws_sfn_state_machine.dengue_batch.arn
}

output "dengue_batch_alerts_topic_arn" {
  description = "SNS topic that receives dengue batch failure alarms."
  value       = aws_sns_topic.dengue_batch_alerts.arn
}
