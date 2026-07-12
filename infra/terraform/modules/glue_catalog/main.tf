resource "aws_glue_catalog_database" "this" {
  for_each = var.databases

  name        = each.key
  description = each.value.description

  parameters = merge(
    var.default_parameters,
    {
      layer = each.key
    }
  )
}