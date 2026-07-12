output "database_names" {
  description = "Created Glue Catalog database names."
  value       = { for key, db in aws_glue_catalog_database.this : key => db.name }
}