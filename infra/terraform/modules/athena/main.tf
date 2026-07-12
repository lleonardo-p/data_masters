resource "aws_athena_workgroup" "this" {
  name        = var.workgroup_name
  description = "Athena workgroup for BAIP analytical queries."
  state       = "ENABLED"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = var.bytes_scanned_cutoff_per_query

    result_configuration {
      output_location = "s3://${var.results_bucket_name}/${var.results_prefix}"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = merge(
    var.tags,
    {
      Name = var.workgroup_name
    }
  )
}