variable "job_name" {
  description = "AWS Glue job name."
  type        = string
}

variable "role_arn" {
  description = "IAM role ARN used by AWS Glue job."
  type        = string
}

variable "script_location" {
  description = "S3 location of the Glue script."
  type        = string
}

variable "glue_version" {
  description = "AWS Glue version."
  type        = string
  default     = "5.0"
}

variable "worker_type" {
  description = "Glue worker type."
  type        = string
  default     = "G.1X"
}

variable "number_of_workers" {
  description = "Number of Glue workers."
  type        = number
  default     = 2
}

variable "timeout" {
  description = "Glue job timeout in minutes."
  type        = number
  default     = 10
}

variable "max_retries" {
  description = "Maximum number of retries."
  type        = number
  default     = 0
}

variable "default_arguments" {
  description = "Default arguments passed to the Glue job."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Additional tags for Glue job."
  type        = map(string)
  default     = {}
}