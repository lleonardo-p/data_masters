locals {
  dengue_nrt_api_name = "${var.project_name}-${var.environment}-dengue-nrt-api"
  dengue_nrt_api_path = "${path.root}/../../../../src/lambda/dengue_nrt_api"
}

data "archive_file" "dengue_nrt_api" {
  type        = "zip"
  output_path = "${path.root}/.terraform/dengue_nrt_api.zip"

  source {
    content  = file("${local.dengue_nrt_api_path}/identity.py")
    filename = "identity.py"
  }

  source {
    content  = file("${local.dengue_nrt_api_path}/lambda_function.py")
    filename = "lambda_function.py"
  }

  source {
    content  = file("${local.dengue_nrt_api_path}/service.py")
    filename = "service.py"
  }
}

data "aws_iam_policy_document" "dengue_nrt_api_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "dengue_nrt_api" {
  name               = "${local.dengue_nrt_api_name}-role"
  assume_role_policy = data.aws_iam_policy_document.dengue_nrt_api_assume_role.json

  tags = {
    purpose = "dengue-nrt-api"
  }
}

resource "aws_iam_role_policy_attachment" "dengue_nrt_api_logs" {
  role       = aws_iam_role.dengue_nrt_api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "dengue_nrt_api" {
  statement {
    sid       = "GenerateCpfHmac"
    effect    = "Allow"
    actions   = ["kms:GenerateMac"]
    resources = [aws_kms_key.dengue_nrt_cpf_hmac.arn]
  }

  statement {
    sid    = "ReadNrtTables"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query"
    ]
    resources = [
      aws_dynamodb_table.dengue_nrt_tokens.arn,
      aws_dynamodb_table.dengue_nrt_history.arn,
      aws_dynamodb_table.dengue_nrt_indicators.arn
    ]
  }
}

resource "aws_iam_role_policy" "dengue_nrt_api" {
  name   = "${local.dengue_nrt_api_name}-policy"
  role   = aws_iam_role.dengue_nrt_api.id
  policy = data.aws_iam_policy_document.dengue_nrt_api.json
}

resource "aws_cloudwatch_log_group" "dengue_nrt_api" {
  name              = "/aws/lambda/${local.dengue_nrt_api_name}"
  retention_in_days = 30

  tags = {
    purpose = "dengue-nrt-api"
  }
}

resource "aws_lambda_function" "dengue_nrt_api" {
  function_name = local.dengue_nrt_api_name
  description   = "Reads dengue NRT indicators and pseudonymized patient history."
  role          = aws_iam_role.dengue_nrt_api.arn

  filename         = data.archive_file.dengue_nrt_api.output_path
  source_code_hash = data.archive_file.dengue_nrt_api.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]

  memory_size = 256
  timeout     = 15

  environment {
    variables = {
      AGGREGATE_SHARD_COUNT = "8"
      HISTORY_TABLE_NAME    = aws_dynamodb_table.dengue_nrt_history.name
      HMAC_KEY_ARN          = aws_kms_key.dengue_nrt_cpf_hmac.arn
      INDICATORS_TABLE_NAME = aws_dynamodb_table.dengue_nrt_indicators.name
      LOG_LEVEL             = "INFO"
      TOKEN_TABLE_NAME      = aws_dynamodb_table.dengue_nrt_tokens.name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.dengue_nrt_api,
    aws_iam_role_policy.dengue_nrt_api,
    aws_iam_role_policy_attachment.dengue_nrt_api_logs
  ]

  tags = {
    purpose = "dengue-nrt-api"
    layer   = "nrt"
  }
}

resource "aws_apigatewayv2_api" "dengue_nrt" {
  name          = local.dengue_nrt_api_name
  protocol_type = "HTTP"

  tags = {
    purpose = "dengue-nrt-api"
  }
}

resource "aws_apigatewayv2_integration" "dengue_nrt" {
  api_id                 = aws_apigatewayv2_api.dengue_nrt.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.dengue_nrt_api.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 15000
}

resource "aws_apigatewayv2_route" "dengue_nrt_health" {
  api_id             = aws_apigatewayv2_api.dengue_nrt.id
  route_key          = "GET /health"
  authorization_type = "NONE"
  target             = "integrations/${aws_apigatewayv2_integration.dengue_nrt.id}"
}

resource "aws_apigatewayv2_route" "dengue_nrt_indicators" {
  api_id             = aws_apigatewayv2_api.dengue_nrt.id
  route_key          = "GET /v1/indicators"
  authorization_type = "AWS_IAM"
  target             = "integrations/${aws_apigatewayv2_integration.dengue_nrt.id}"
}

resource "aws_apigatewayv2_route" "dengue_nrt_patient_history" {
  api_id             = aws_apigatewayv2_api.dengue_nrt.id
  route_key          = "POST /v1/patients/history"
  authorization_type = "AWS_IAM"
  target             = "integrations/${aws_apigatewayv2_integration.dengue_nrt.id}"
}

resource "aws_cloudwatch_log_group" "dengue_nrt_api_access" {
  name              = "/aws/apigateway/${local.dengue_nrt_api_name}"
  retention_in_days = 30

  tags = {
    purpose = "dengue-nrt-api-access"
  }
}

resource "aws_apigatewayv2_stage" "dengue_nrt" {
  api_id      = aws_apigatewayv2_api.dengue_nrt.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    detailed_metrics_enabled = true
    throttling_burst_limit   = 50
    throttling_rate_limit    = 25
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.dengue_nrt_api_access.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      responseLength   = "$context.responseLength"
      sourceIp         = "$context.identity.sourceIp"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  tags = {
    purpose = "dengue-nrt-api"
  }
}

resource "aws_lambda_permission" "dengue_nrt_api_gateway" {
  statement_id  = "AllowDengueNrtApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dengue_nrt_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.dengue_nrt.execution_arn}/*/*"
}

resource "aws_cloudwatch_metric_alarm" "dengue_nrt_api_errors" {
  alarm_name          = "${local.dengue_nrt_api_name}-errors"
  alarm_description   = "The dengue NRT API Lambda returned an error."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.dengue_nrt_api.function_name
  }

  alarm_actions = [aws_sns_topic.dengue_nrt_alerts.arn]

  tags = {
    purpose = "dengue-nrt-api-alert"
  }
}

resource "aws_cloudwatch_metric_alarm" "dengue_nrt_api_5xx" {
  alarm_name          = "${local.dengue_nrt_api_name}-5xx"
  alarm_description   = "The dengue NRT HTTP API returned a 5xx response."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "5xx"
  namespace           = "AWS/ApiGateway"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.dengue_nrt.id
    Stage = aws_apigatewayv2_stage.dengue_nrt.name
  }

  alarm_actions = [aws_sns_topic.dengue_nrt_alerts.arn]

  tags = {
    purpose = "dengue-nrt-api-alert"
  }
}
