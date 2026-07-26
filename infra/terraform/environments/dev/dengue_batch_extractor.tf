locals {
  dengue_batch_extractor_name   = "${var.project_name}-${var.environment}-dengue-batch-extractor"
  dengue_batch_extractor_path   = "${path.root}/../../../../src/lambda/dengue_batch_extractor"
  dengue_source_api_secret_name = "${var.project_name}/${var.environment}/dengue-source-api-key"
}

data "archive_file" "dengue_batch_extractor" {
  type = "zip"

  output_path = "${path.root}/.terraform/dengue_batch_extractor.zip"

  source {
    content  = file("${local.dengue_batch_extractor_path}/contract.py")
    filename = "contract.py"
  }

  source {
    content  = file("${local.dengue_batch_extractor_path}/lambda_function.py")
    filename = "lambda_function.py"
  }

  source {
    content  = file("${local.dengue_batch_extractor_path}/streaming.py")
    filename = "streaming.py"
  }
}

data "aws_iam_policy_document" "dengue_batch_extractor_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "dengue_batch_extractor" {
  name = "${local.dengue_batch_extractor_name}-role"

  assume_role_policy = data.aws_iam_policy_document.dengue_batch_extractor_assume_role.json

  tags = {
    purpose = "dengue-batch-extraction"
  }
}

resource "aws_iam_role_policy_attachment" "dengue_batch_extractor_logs" {
  role       = aws_iam_role.dengue_batch_extractor.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_secretsmanager_secret" "dengue_source_api_key" {
  name                    = local.dengue_source_api_secret_name
  description             = "API key for the external dengue source API."
  recovery_window_in_days = 7

  tags = {
    purpose = "dengue-source-api-authentication"
  }
}

data "aws_iam_policy_document" "dengue_batch_extractor" {
  statement {
    sid    = "ReadWriteDengueStaging"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]

    resources = [
      "${module.data_lake_bucket.bucket_arn}/staging/opendatasus/dengue/*"
    ]
  }

  statement {
    sid    = "ReadDengueSourceApiKey"
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = [
      aws_secretsmanager_secret.dengue_source_api_key.arn,
    ]
  }
  statement {
    sid    = "ListDengueStaging"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      module.data_lake_bucket.bucket_arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"

      values = [
        "staging/opendatasus/dengue/*",
      ]
    }
  }

}

resource "aws_iam_role_policy" "dengue_batch_extractor" {
  name   = "${local.dengue_batch_extractor_name}-policy"
  role   = aws_iam_role.dengue_batch_extractor.id
  policy = data.aws_iam_policy_document.dengue_batch_extractor.json
}

resource "aws_cloudwatch_log_group" "dengue_batch_extractor" {
  name              = "/aws/lambda/${local.dengue_batch_extractor_name}"
  retention_in_days = 30

  tags = {
    purpose = "dengue-batch-extraction"
  }
}

resource "aws_lambda_function" "dengue_batch_extractor" {
  function_name = local.dengue_batch_extractor_name
  description   = "Extracts dengue data from the external API into S3 Staging."
  role          = aws_iam_role.dengue_batch_extractor.arn

  filename         = data.archive_file.dengue_batch_extractor.output_path
  source_code_hash = data.archive_file.dengue_batch_extractor.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]

  memory_size = 512
  timeout     = 900

  environment {
    variables = {
      ALLOWED_API_HOST_SUFFIXES = ".ngrok-free.app,.ngrok-free.dev"
      API_KEY_SECRET_ARN        = aws_secretsmanager_secret.dengue_source_api_key.arn
      DESTINATION_BUCKET        = module.data_lake_bucket.bucket_name
      DESTINATION_PREFIX        = "staging/opendatasus/dengue"
      ENVIRONMENT               = var.environment
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.dengue_batch_extractor,
    aws_iam_role_policy.dengue_batch_extractor,
    aws_iam_role_policy_attachment.dengue_batch_extractor_logs,
  ]

  tags = {
    purpose = "dengue-batch-extraction"
    layer   = "staging"
  }
}
