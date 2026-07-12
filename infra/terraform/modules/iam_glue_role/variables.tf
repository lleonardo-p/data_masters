variable "role_name" {
  description = "IAM role name used by AWS Glue jobs."
  type        = string
}

variable "policy_name" {
  description = "IAM policy name for Glue S3 access."
  type        = string
}

variable "data_lake_bucket_arn" {
  description = "ARN of the main Data Lake S3 bucket."
  type        = string
}

variable "artifacts_bucket_arn" {
  description = "ARN of the artifacts S3 bucket."
  type        = string
}

variable "logs_bucket_arn" {
  description = "ARN of the logs S3 bucket."
  type        = string
}

variable "tags" {
  description = "Additional tags for IAM resources."
  type        = map(string)
  default     = {}
}