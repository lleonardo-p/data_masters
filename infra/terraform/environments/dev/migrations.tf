moved {
  from = aws_s3_object.silver_arbovirus_cases_script
  to   = aws_s3_object.silver_dengue_cases_script
}

moved {
  from = module.silver_arbovirus_cases_glue_job
  to   = module.silver_dengue_cases_glue_job
}