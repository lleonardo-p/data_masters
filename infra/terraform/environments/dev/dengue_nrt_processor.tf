locals {
  dengue_nrt_processor_name = "${var.project_name}-${var.environment}-dengue-nrt-processor"
  dengue_nrt_processor_path = "${path.root}/../../../../src/lambda/dengue_nrt_processor"

  dengue_nrt_token_table_name       = "${var.project_name}-${var.environment}-dengue-patient-tokens"
  dengue_nrt_history_table_name     = "${var.project_name}-${var.environment}-dengue-triage-history"
  dengue_nrt_indicators_table_name  = "${var.project_name}-${var.environment}-dengue-nrt-indicators"
  dengue_nrt_idempotency_table_name = "${var.project_name}-${var.environment}-dengue-nrt-idempotency"
}

data "archive_file" "dengue_nrt_processor" {
  type        = "zip"
  output_path = "${path.root}/.terraform/dengue_nrt_processor.zip"

  source {
    content  = file("${local.dengue_nrt_processor_path}/contract.py")
    filename = "contract.py"
  }

  source {
    content  = file("${local.dengue_nrt_processor_path}/identity.py")
    filename = "identity.py"
  }

  source {
    content  = file("${local.dengue_nrt_processor_path}/lambda_function.py")
    filename = "lambda_function.py"
  }

  source {
    content  = file("${local.dengue_nrt_processor_path}/storage.py")
    filename = "storage.py"
  }
}

resource "aws_kms_key" "dengue_nrt_cpf_hmac" {
  description              = "HMAC key used to pseudonymize CPF in the dengue NRT flow."
  customer_master_key_spec = "HMAC_256"
  key_usage                = "GENERATE_VERIFY_MAC"
  deletion_window_in_days  = 30

  tags = {
    purpose = "dengue-nrt-cpf-pseudonymization"
  }
}

resource "aws_kms_alias" "dengue_nrt_cpf_hmac" {
  name          = "alias/${local.dengue_nrt_processor_name}-cpf-hmac"
  target_key_id = aws_kms_key.dengue_nrt_cpf_hmac.key_id
}

resource "aws_dynamodb_table" "dengue_nrt_tokens" {
  name         = local.dengue_nrt_token_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cpf_fingerprint"

  attribute {
    name = "cpf_fingerprint"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    purpose             = "dengue-nrt-token-vault"
    data_classification = "restricted-pseudonymous"
  }
}

resource "aws_dynamodb_table" "dengue_nrt_history" {
  name         = local.dengue_nrt_history_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "patient_token"
  range_key    = "event_sort_key"

  attribute {
    name = "patient_token"
    type = "S"
  }

  attribute {
    name = "event_sort_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    purpose             = "dengue-nrt-pseudonymized-history"
    data_classification = "pseudonymous-health-data"
  }
}

resource "aws_dynamodb_table" "dengue_nrt_indicators" {
  name         = local.dengue_nrt_indicators_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "scope_key"
  range_key    = "minute_bucket"

  attribute {
    name = "scope_key"
    type = "S"
  }

  attribute {
    name = "minute_bucket"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    purpose             = "dengue-nrt-operational-indicators"
    data_classification = "aggregated"
  }
}

resource "aws_dynamodb_table" "dengue_nrt_idempotency" {
  name         = local.dengue_nrt_idempotency_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    purpose             = "dengue-nrt-idempotency"
    data_classification = "technical"
  }
}

data "aws_iam_policy_document" "dengue_nrt_processor_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "dengue_nrt_processor" {
  name               = "${local.dengue_nrt_processor_name}-role"
  assume_role_policy = data.aws_iam_policy_document.dengue_nrt_processor_assume_role.json

  tags = {
    purpose = "dengue-nrt-processing"
  }
}

resource "aws_iam_role_policy_attachment" "dengue_nrt_processor_logs" {
  role       = aws_iam_role.dengue_nrt_processor.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "dengue_nrt_processor" {
  statement {
    sid    = "ConsumeTriageQueue"
    effect = "Allow"

    actions = [
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ReceiveMessage"
    ]

    resources = [aws_sqs_queue.dengue_nrt.arn]
  }

  statement {
    sid    = "GenerateCpfHmac"
    effect = "Allow"

    actions   = ["kms:GenerateMac"]
    resources = [aws_kms_key.dengue_nrt_cpf_hmac.arn]
  }

  statement {
    sid    = "ReadWriteNrtTables"
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:TransactWriteItems",
      "dynamodb:UpdateItem"
    ]

    resources = [
      aws_dynamodb_table.dengue_nrt_tokens.arn,
      aws_dynamodb_table.dengue_nrt_history.arn,
      aws_dynamodb_table.dengue_nrt_indicators.arn,
      aws_dynamodb_table.dengue_nrt_idempotency.arn
    ]
  }
}

resource "aws_iam_role_policy" "dengue_nrt_processor" {
  name   = "${local.dengue_nrt_processor_name}-policy"
  role   = aws_iam_role.dengue_nrt_processor.id
  policy = data.aws_iam_policy_document.dengue_nrt_processor.json
}

resource "aws_cloudwatch_log_group" "dengue_nrt_processor" {
  name              = "/aws/lambda/${local.dengue_nrt_processor_name}"
  retention_in_days = 30

  tags = {
    purpose = "dengue-nrt-processing"
  }
}

resource "aws_lambda_function" "dengue_nrt_processor" {
  function_name = local.dengue_nrt_processor_name
  description   = "Validates, pseudonymizes and persists dengue NRT triage events."
  role          = aws_iam_role.dengue_nrt_processor.arn

  filename         = data.archive_file.dengue_nrt_processor.output_path
  source_code_hash = data.archive_file.dengue_nrt_processor.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]

  memory_size = 256
  timeout     = 30

  environment {
    variables = {
      AGGREGATE_SHARD_COUNT  = "8"
      ENVIRONMENT            = var.environment
      HISTORY_TABLE_NAME     = aws_dynamodb_table.dengue_nrt_history.name
      HMAC_KEY_ARN           = aws_kms_key.dengue_nrt_cpf_hmac.arn
      HMAC_KEY_VERSION       = "v1"
      IDEMPOTENCY_TABLE_NAME = aws_dynamodb_table.dengue_nrt_idempotency.name
      INDICATORS_TABLE_NAME  = aws_dynamodb_table.dengue_nrt_indicators.name
      LOG_LEVEL              = "INFO"
      TOKEN_TABLE_NAME       = aws_dynamodb_table.dengue_nrt_tokens.name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.dengue_nrt_processor,
    aws_iam_role_policy.dengue_nrt_processor,
    aws_iam_role_policy_attachment.dengue_nrt_processor_logs
  ]

  tags = {
    purpose = "dengue-nrt-processing"
    layer   = "nrt"
  }
}

resource "aws_lambda_event_source_mapping" "dengue_nrt_processor" {
  event_source_arn = aws_sqs_queue.dengue_nrt.arn
  function_name    = aws_lambda_function.dengue_nrt_processor.arn
  enabled          = true

  batch_size                         = 10
  maximum_batching_window_in_seconds = 2
  function_response_types            = ["ReportBatchItemFailures"]

  scaling_config {
    maximum_concurrency = 5
  }

  depends_on = [aws_iam_role_policy.dengue_nrt_processor]
}

resource "aws_cloudwatch_metric_alarm" "dengue_nrt_processor_errors" {
  alarm_name          = "${local.dengue_nrt_processor_name}-errors"
  alarm_description   = "The dengue NRT processor Lambda returned an error."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.dengue_nrt_processor.function_name
  }

  alarm_actions = [aws_sns_topic.dengue_nrt_alerts.arn]

  tags = {
    purpose = "dengue-nrt-processor-alert"
  }
}
