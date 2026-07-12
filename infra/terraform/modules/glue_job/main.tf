resource "aws_glue_job" "this" {
  name     = var.job_name
  role_arn = var.role_arn

  glue_version      = var.glue_version
  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers

  timeout     = var.timeout
  max_retries = var.max_retries

  command {
    name            = "glueetl"
    script_location = var.script_location
    python_version  = "3"
  }

  default_arguments = merge(
    {
      "--enable-metrics"                   = "true"
      "--enable-continuous-cloudwatch-log" = "true"
      "--enable-job-insights"              = "true"
      "--job-language"                     = "python"
    },
    var.default_arguments
  )

  tags = merge(
    var.tags,
    {
      Name = var.job_name
    }
  )
}