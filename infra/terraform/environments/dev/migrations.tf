moved {
  from = aws_s3_object.silver_arbovirus_cases_script
  to   = aws_s3_object.silver_dengue_cases_script
}

moved {
  from = module.silver_arbovirus_cases_glue_job
  to   = module.silver_dengue_cases_glue_job
}

moved {
  from = aws_s3_object.bronze_ingestion_script
  to   = aws_s3_object.dengue_staging_to_bronze_script
}

moved {
  from = module.bronze_ingestion_glue_job
  to   = module.dengue_staging_to_bronze_glue_job
}

moved {
  from = aws_s3_object.silver_dengue_cases_script
  to   = aws_s3_object.dengue_bronze_to_silver_script
}

moved {
  from = module.silver_dengue_cases_glue_job
  to   = module.dengue_bronze_to_silver_glue_job
}

moved {
  from = aws_s3_object.gold_dengue_script
  to   = aws_s3_object.dengue_silver_to_gold_script
}

moved {
  from = module.gold_dengue_glue_job
  to   = module.dengue_silver_to_gold_glue_job
}
