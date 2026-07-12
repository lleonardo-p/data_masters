output "job_name" {
  description = "AWS Glue job name."
  value       = aws_glue_job.this.name
}

output "job_arn" {
  description = "AWS Glue job ARN."
  value       = aws_glue_job.this.arn
}