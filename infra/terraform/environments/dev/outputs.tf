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