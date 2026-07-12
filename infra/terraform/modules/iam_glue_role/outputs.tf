output "role_name" {
  description = "IAM role name used by AWS Glue jobs."
  value       = aws_iam_role.this.name
}

output "role_arn" {
  description = "IAM role ARN used by AWS Glue jobs."
  value       = aws_iam_role.this.arn
}

output "policy_arn" {
  description = "Custom IAM policy ARN for Glue S3 access."
  value       = aws_iam_policy.glue_s3_access.arn
}