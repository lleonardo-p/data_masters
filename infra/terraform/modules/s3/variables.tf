variable "bucket_name" {
  description = "Name of the S3 bucket."
  type        = string
}

variable "force_destroy" {
  description = "Whether all objects should be deleted from the bucket when destroying it."
  type        = bool
  default     = false
}

variable "prefixes" {
  description = "List of logical folder prefixes to create in the bucket."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional tags for the bucket."
  type        = map(string)
  default     = {}
}