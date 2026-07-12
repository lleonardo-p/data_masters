variable "workgroup_name" {
  description = "Athena workgroup name."
  type        = string
}

variable "results_bucket_name" {
  description = "S3 bucket used to store Athena query results."
  type        = string
}

variable "results_prefix" {
  description = "S3 prefix used to store Athena query results."
  type        = string
  default     = "query-results/"
}

variable "bytes_scanned_cutoff_per_query" {
  description = "Maximum bytes scanned per Athena query."
  type        = number
  default     = 1073741824 # 1 GB
}

variable "tags" {
  description = "Additional tags for Athena workgroup."
  type        = map(string)
  default     = {}
}