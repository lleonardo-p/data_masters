variable "aws_region" {
  description = "AWS region used for the bootstrap resources."
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