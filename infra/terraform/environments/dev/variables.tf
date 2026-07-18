variable "aws_region" {
  description = "AWS region used for BAIP resources."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile used by Terraform."
  type        = string
  default     = "baip-dev"
}

variable "project_name" {
  description = "Project name."
  type        = string
  default     = "baip"
}

variable "environment" {
  description = "Environment name."
  type        = string
  default     = "dev"
}

variable "enable_quicksight_dengue" {
  description = "Creates the optional QuickSight Athena data source and dengue SPICE dataset. The QuickSight subscription must already exist."
  type        = bool
  default     = false
}

variable "quicksight_author_arn" {
  description = "QuickSight author ARN that owns the dengue data source and datasets. Required when enable_quicksight_dengue is true."
  type        = string
  default     = ""

  validation {
    condition = (
      !var.enable_quicksight_dengue ||
      can(regex("^arn:aws[a-z-]*:quicksight:[a-z0-9-]+:[0-9]{12}:user/[^/]+/.+$", var.quicksight_author_arn))
    )
    error_message = "quicksight_author_arn must be a valid QuickSight user ARN when enable_quicksight_dengue is true."
  }
}
