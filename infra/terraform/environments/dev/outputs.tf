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

output "dengue_staging_to_bronze_glue_job_name" {
  description = "Dengue Staging-to-Bronze AWS Glue job name."
  value       = module.dengue_staging_to_bronze_glue_job.job_name
}

output "dengue_staging_to_bronze_glue_job_arn" {
  description = "Dengue Staging-to-Bronze AWS Glue job ARN."
  value       = module.dengue_staging_to_bronze_glue_job.job_arn
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

output "dengue_bronze_to_silver_glue_job_name" {
  description = "Dengue Bronze-to-Silver AWS Glue job name."
  value       = module.dengue_bronze_to_silver_glue_job.job_name
}

output "dengue_bronze_to_silver_glue_job_arn" {
  description = "Dengue Bronze-to-Silver AWS Glue job ARN."
  value       = module.dengue_bronze_to_silver_glue_job.job_arn
}

output "gold_dengue_output_path" {
  description = "S3 root path for the dengue dimensional model."
  value       = local.gold_dengue_output_path
}

output "dengue_silver_to_gold_glue_job_name" {
  description = "Dengue Silver-to-Gold AWS Glue job name."
  value       = module.dengue_silver_to_gold_glue_job.job_name
}

output "dengue_silver_to_gold_glue_job_arn" {
  description = "Dengue Silver-to-Gold AWS Glue job ARN."
  value       = module.dengue_silver_to_gold_glue_job.job_arn
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

output "dengue_batch_extractor_function_name" {
  description = "Lambda function that extracts dengue data into S3 Staging."
  value       = aws_lambda_function.dengue_batch_extractor.function_name
}

output "dengue_batch_extractor_function_arn" {
  description = "ARN of the dengue Batch extractor Lambda function."
  value       = aws_lambda_function.dengue_batch_extractor.arn
}

output "dengue_source_api_secret_name" {
  description = "Secrets Manager secret that stores the dengue source API key."
  value       = aws_secretsmanager_secret.dengue_source_api_key.name
}

output "dengue_nrt_queue_name" {
  description = "Name of the SQS queue that receives synthetic dengue triage events."
  value       = aws_sqs_queue.dengue_nrt.name
}

output "dengue_nrt_queue_url" {
  description = "URL used by the hospital simulator to publish dengue triage events."
  value       = aws_sqs_queue.dengue_nrt.url
}

output "dengue_nrt_queue_arn" {
  description = "ARN of the SQS queue that receives synthetic dengue triage events."
  value       = aws_sqs_queue.dengue_nrt.arn
}

output "dengue_nrt_dlq_name" {
  description = "Name of the dengue NRT dead-letter queue."
  value       = aws_sqs_queue.dengue_nrt_dlq.name
}

output "dengue_nrt_dlq_url" {
  description = "URL of the dengue NRT dead-letter queue."
  value       = aws_sqs_queue.dengue_nrt_dlq.url
}

output "dengue_nrt_dlq_arn" {
  description = "ARN of the dengue NRT dead-letter queue."
  value       = aws_sqs_queue.dengue_nrt_dlq.arn
}

output "dengue_nrt_producer_policy_arn" {
  description = "IAM policy ARN for principals that publish synthetic triage events."
  value       = aws_iam_policy.dengue_nrt_producer.arn
}

output "dengue_nrt_alerts_topic_arn" {
  description = "SNS topic that receives dengue NRT queue alarms."
  value       = aws_sns_topic.dengue_nrt_alerts.arn
}

output "dengue_nrt_processor_function_name" {
  description = "Name of the Lambda that processes dengue NRT triage events."
  value       = aws_lambda_function.dengue_nrt_processor.function_name
}

output "dengue_nrt_processor_function_arn" {
  description = "ARN of the Lambda that processes dengue NRT triage events."
  value       = aws_lambda_function.dengue_nrt_processor.arn
}

output "dengue_nrt_cpf_hmac_key_arn" {
  description = "ARN of the KMS HMAC key used to pseudonymize CPF values."
  value       = aws_kms_key.dengue_nrt_cpf_hmac.arn
}

output "dengue_nrt_token_table_name" {
  description = "DynamoDB table that maps CPF fingerprints to patient tokens."
  value       = aws_dynamodb_table.dengue_nrt_tokens.name
}

output "dengue_nrt_history_table_name" {
  description = "DynamoDB table containing pseudonymized triage history."
  value       = aws_dynamodb_table.dengue_nrt_history.name
}

output "dengue_nrt_indicators_table_name" {
  description = "DynamoDB table containing sharded NRT indicators."
  value       = aws_dynamodb_table.dengue_nrt_indicators.name
}

output "dengue_nrt_idempotency_table_name" {
  description = "DynamoDB table used to prevent duplicate event processing."
  value       = aws_dynamodb_table.dengue_nrt_idempotency.name
}

output "dengue_nrt_api_url" {
  description = "Base URL of the dengue NRT HTTP API."
  value       = aws_apigatewayv2_api.dengue_nrt.api_endpoint
}

output "dengue_nrt_api_function_name" {
  description = "Name of the Lambda that serves dengue NRT queries."
  value       = aws_lambda_function.dengue_nrt_api.function_name
}

output "dengue_nrt_api_id" {
  description = "API Gateway HTTP API identifier for dengue NRT queries."
  value       = aws_apigatewayv2_api.dengue_nrt.id
}
