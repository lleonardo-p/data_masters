variable "databases" {
  description = "Glue Catalog databases to create."
  type = map(object({
    description = string
  }))
}

variable "default_parameters" {
  description = "Default metadata parameters for Glue databases."
  type        = map(string)
  default     = {}
}