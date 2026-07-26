locals {
  dengue_batch_reconciliation_job_name    = "${var.project_name}-${var.environment}-dengue-batch-reconciliation"
  dengue_batch_reconciliation_script_key  = "glue/scripts/reconcile_dengue_batch/reconcile_dengue_batch.py"
  dengue_batch_reconciliation_script_path = "${path.root}/../../../../src/glue/jobs/reconcile_dengue_batch/reconcile_dengue_batch.py"
  dengue_batch_reconciliation_output_path = "s3://${module.logs_bucket.bucket_name}/pipeline-runs/dengue-batch/reconciliation/"

  dengue_batch_state_machine_name = "${var.project_name}-${var.environment}-dengue-batch-pipeline"
  dengue_batch_alerts_topic_name  = "${var.project_name}-${var.environment}-dengue-batch-alerts"

  dengue_batch_terminal_metrics = {
    failed    = "ExecutionsFailed"
    timed_out = "ExecutionsTimedOut"
    aborted   = "ExecutionsAborted"
  }
}

resource "aws_s3_object" "dengue_batch_reconciliation_script" {
  bucket = module.artifacts_bucket.bucket_name
  key    = local.dengue_batch_reconciliation_script_key
  source = local.dengue_batch_reconciliation_script_path

  source_hash = filemd5(local.dengue_batch_reconciliation_script_path)

  tags = {
    purpose = "glue-script"
    layer   = "audit"
  }
}

module "dengue_batch_reconciliation_glue_job" {
  source = "../../modules/glue_job"

  job_name        = local.dengue_batch_reconciliation_job_name
  role_arn        = module.iam_glue_role.role_arn
  script_location = "s3://${module.artifacts_bucket.bucket_name}/${aws_s3_object.dengue_batch_reconciliation_script.key}"

  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60
  max_retries       = 0

  default_arguments = {
    "--BATCH_ID"                   = "manual"
    "--ENVIRONMENT"                = var.environment
    "--BRONZE_INPUT_PATH"          = local.bronze_dengue_output_path
    "--SILVER_INPUT_PATH"          = local.silver_dengue_cases_output_path
    "--QUARANTINE_INPUT_PATH"      = local.silver_dengue_quarantine_path
    "--GOLD_INPUT_PATH"            = local.gold_dengue_output_path
    "--RECONCILIATION_OUTPUT_PATH" = local.dengue_batch_reconciliation_output_path
    "--FAIL_ON_MISMATCH"           = "true"
  }

  tags = {
    purpose = "dengue-batch-reconciliation"
    layer   = "audit"
  }
}

data "aws_iam_policy_document" "dengue_batch_step_functions_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "dengue_batch_step_functions" {
  name               = "${local.dengue_batch_state_machine_name}-role"
  assume_role_policy = data.aws_iam_policy_document.dengue_batch_step_functions_assume_role.json

  tags = {
    purpose = "dengue-batch-orchestration"
  }
}

data "aws_iam_policy_document" "dengue_batch_step_functions" {
  statement {
    sid    = "RunDengueGlueJobs"
    effect = "Allow"

    actions = [
      "glue:BatchStopJobRun",
      "glue:GetJobRun",
      "glue:GetJobRuns",
      "glue:StartJobRun"
    ]

    resources = [
      module.bronze_ingestion_glue_job.job_arn,
      module.silver_dengue_cases_glue_job.job_arn,
      module.gold_dengue_glue_job.job_arn,
      module.dengue_batch_reconciliation_glue_job.job_arn
    ]
  }

  statement {
    sid    = "RunDengueGoldCrawler"
    effect = "Allow"

    actions = [
      "glue:GetCrawler",
      "glue:StartCrawler"
    ]

    resources = [aws_glue_crawler.gold_dengue.arn]
  }

  statement {
    sid    = "DeliverStepFunctionsLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:DescribeLogGroups",
      "logs:DescribeResourcePolicies",
      "logs:GetLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:UpdateLogDelivery"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "dengue_batch_step_functions" {
  name   = "${local.dengue_batch_state_machine_name}-policy"
  role   = aws_iam_role.dengue_batch_step_functions.id
  policy = data.aws_iam_policy_document.dengue_batch_step_functions.json
}

resource "aws_cloudwatch_log_group" "dengue_batch_step_functions" {
  name              = "/aws/vendedlogs/states/${local.dengue_batch_state_machine_name}"
  retention_in_days = 30

  tags = {
    purpose = "dengue-batch-orchestration"
  }
}

resource "aws_sfn_state_machine" "dengue_batch" {
  name     = local.dengue_batch_state_machine_name
  role_arn = aws_iam_role.dengue_batch_step_functions.arn
  type     = "STANDARD"

  definition = jsonencode({
    Comment        = "Orchestrates and reconciles the complete dengue batch pipeline."
    StartAt        = "RunBronze"
    TimeoutSeconds = 14400
    States = {
      RunBronze = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = module.bronze_ingestion_glue_job.job_name
          Arguments = {
            "--BATCH_ID.$"           = "$$.Execution.Name"
            "--STAGING_INPUT_PATH.$" = "$.staging_input_path"
          }
        }
        ResultPath = "$.bronze"
        Next       = "RunSilver"
      }
      RunSilver = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = module.silver_dengue_cases_glue_job.job_name
          Arguments = {
            "--BATCH_ID.$"          = "$$.Execution.Name"
            "--BRONZE_INPUT_PATH.$" = "$.bronze_input_path"
          }
        }
        ResultPath = "$.silver"
        Next       = "RunGold"
      }
      RunGold = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = module.gold_dengue_glue_job.job_name
          Arguments = {
            "--BATCH_ID.$" = "$$.Execution.Name"
          }
        }
        ResultPath = "$.gold"
        Next       = "ReconcileBatch"
      }
      ReconcileBatch = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = module.dengue_batch_reconciliation_glue_job.job_name
          Arguments = {
            "--BATCH_ID.$" = "$$.Execution.Name"
          }
        }
        ResultPath = "$.reconciliation"
        Next       = "StartGoldCrawler"
      }
      StartGoldCrawler = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:glue:startCrawler"
        Parameters = {
          Name = aws_glue_crawler.gold_dengue.name
        }
        ResultPath = null
        Next       = "WaitForCrawler"
      }
      WaitForCrawler = {
        Type    = "Wait"
        Seconds = 15
        Next    = "GetCrawlerStatus"
      }
      GetCrawlerStatus = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:glue:getCrawler"
        Parameters = {
          Name = aws_glue_crawler.gold_dengue.name
        }
        ResultPath = "$.crawler_result"
        Next       = "IsCrawlerReady"
      }
      IsCrawlerReady = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.crawler_result.Crawler.State"
            StringEquals = "READY"
            Next         = "CheckCrawlerResult"
          }
        ]
        Default = "WaitForCrawler"
      }
      CheckCrawlerResult = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.crawler_result.Crawler.LastCrawl.Status"
            StringEquals = "SUCCEEDED"
            Next         = "PipelineSucceeded"
          },
          {
            Or = [
              {
                Variable     = "$.crawler_result.Crawler.LastCrawl.Status"
                StringEquals = "FAILED"
              },
              {
                Variable     = "$.crawler_result.Crawler.LastCrawl.Status"
                StringEquals = "CANCELLED"
              }
            ]
            Next = "CrawlerFailed"
          }
        ]
        Default = "WaitForCrawler"
      }
      CrawlerFailed = {
        Type  = "Fail"
        Error = "DengueGoldCrawlerFailed"
        Cause = "The Gold crawler did not complete successfully."
      }
      PipelineSucceeded = {
        Type = "Succeed"
      }
    }
  })

  logging_configuration {
    include_execution_data = false
    level                  = "ERROR"
    log_destination        = "${aws_cloudwatch_log_group.dengue_batch_step_functions.arn}:*"
  }

  depends_on = [
    aws_iam_role_policy.dengue_batch_step_functions
  ]

  tags = {
    purpose = "dengue-batch-orchestration"
  }
}

resource "aws_sns_topic" "dengue_batch_alerts" {
  name = local.dengue_batch_alerts_topic_name

  tags = {
    purpose = "dengue-batch-alerts"
  }
}

resource "aws_cloudwatch_metric_alarm" "dengue_batch_terminal_failure" {
  for_each = local.dengue_batch_terminal_metrics

  alarm_name          = "${local.dengue_batch_state_machine_name}-${each.key}"
  alarm_description   = "Dengue batch Step Functions terminal state: ${each.value}."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = each.value
  namespace           = "AWS/States"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.dengue_batch.arn
  }

  alarm_actions = [aws_sns_topic.dengue_batch_alerts.arn]

  tags = {
    purpose = "dengue-batch-alert"
  }
}
