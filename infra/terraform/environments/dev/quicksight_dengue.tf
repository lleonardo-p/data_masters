locals {
  quicksight_dengue_data_source_id = "${var.project_name}-${var.environment}-dengue-athena"
  quicksight_dengue_data_set_id    = "${var.project_name}-${var.environment}-dengue-dashboard"

  quicksight_dengue_columns = [
    { name = "notification_period", type = "DATETIME" },
    { name = "notification_year", type = "INTEGER" },
    { name = "notification_month", type = "STRING" },
    { name = "disease_code", type = "STRING" },
    { name = "disease_name", type = "STRING" },
    { name = "municipality_code_ibge", type = "STRING" },
    { name = "municipality_name", type = "STRING" },
    { name = "uf_abbreviation", type = "STRING" },
    { name = "uf_name", type = "STRING" },
    { name = "region_name", type = "STRING" },
    { name = "age_group_name", type = "STRING" },
    { name = "classification_code", type = "STRING" },
    { name = "classification_name", type = "STRING" },
    { name = "notification_count", type = "INTEGER" },
    { name = "confirmed_case_count", type = "INTEGER" },
    { name = "discarded_case_count", type = "INTEGER" },
    { name = "alarm_case_count", type = "INTEGER" },
    { name = "severe_case_count", type = "INTEGER" },
    { name = "under_investigation_count", type = "INTEGER" },
    { name = "hospitalized_case_count", type = "INTEGER" },
    { name = "death_by_disease_count", type = "INTEGER" },
    { name = "death_other_cause_count", type = "INTEGER" },
    { name = "autochthonous_case_count", type = "INTEGER" },
    { name = "quality_warning_count", type = "INTEGER" }
  ]
}

resource "aws_quicksight_data_source" "dengue_athena" {
  count = var.enable_quicksight_dengue ? 1 : 0

  data_source_id = local.quicksight_dengue_data_source_id
  name           = "BAIP Dengue - Athena"
  type           = "ATHENA"

  parameters {
    athena {
      work_group = module.athena.workgroup_name
    }
  }

  permission {
    principal = var.quicksight_author_arn
    actions = [
      "quicksight:DeleteDataSource",
      "quicksight:DescribeDataSource",
      "quicksight:DescribeDataSourcePermissions",
      "quicksight:PassDataSource",
      "quicksight:UpdateDataSource",
      "quicksight:UpdateDataSourcePermissions"
    ]
  }

  tags = {
    purpose = "dengue-dashboard"
    layer   = "consumption"
  }
}

resource "aws_quicksight_data_set" "dengue_dashboard" {
  count = var.enable_quicksight_dengue ? 1 : 0

  data_set_id = local.quicksight_dengue_data_set_id
  name        = "Dengue - panorama epidemiologico"
  import_mode = "SPICE"

  physical_table_map {
    physical_table_map_id = "dengue_dashboard"

    relational_table {
      data_source_arn = aws_quicksight_data_source.dengue_athena[0].arn
      catalog         = "AwsDataCatalog"
      schema          = local.gold_database_name
      name            = "vw_dengue_dashboard"

      dynamic "input_columns" {
        for_each = local.quicksight_dengue_columns

        content {
          name = input_columns.value.name
          type = input_columns.value.type
        }
      }
    }
  }

  permissions {
    principal = var.quicksight_author_arn
    actions = [
      "quicksight:CancelIngestion",
      "quicksight:CreateIngestion",
      "quicksight:DeleteDataSet",
      "quicksight:DescribeDataSet",
      "quicksight:DescribeDataSetPermissions",
      "quicksight:DescribeIngestion",
      "quicksight:ListIngestions",
      "quicksight:PassDataSet",
      "quicksight:UpdateDataSet",
      "quicksight:UpdateDataSetPermissions"
    ]
  }

  depends_on = [aws_quicksight_data_source.dengue_athena]

  tags = {
    purpose = "dengue-dashboard"
    layer   = "consumption"
  }
}
