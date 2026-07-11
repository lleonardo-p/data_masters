output "terraform_state_bucket" {
  description = "S3 bucket used to store Terraform remote state."
  value       = aws_s3_bucket.terraform_state.bucket
}

output "account_id" {
  description = "Current AWS account ID."
  value       = data.aws_caller_identity.current.account_id
}