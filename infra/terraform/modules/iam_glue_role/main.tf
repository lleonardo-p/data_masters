data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "this" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json

  tags = merge(
    var.tags,
    {
      Name = var.role_name
    }
  )
}

data "aws_iam_policy_document" "glue_s3_access" {
  statement {
    sid    = "AllowListBuckets"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]

    resources = [
      var.data_lake_bucket_arn,
      var.artifacts_bucket_arn,
      var.logs_bucket_arn
    ]
  }

  statement {
    sid    = "AllowDataLakeReadWrite"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]

    resources = [
      "${var.data_lake_bucket_arn}/*"
    ]
  }

  statement {
    sid    = "AllowArtifactsRead"
    effect = "Allow"

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${var.artifacts_bucket_arn}/glue/scripts/*",
      "${var.artifacts_bucket_arn}/dependencies/*"
    ]
  }

  statement {
    sid    = "AllowLogsBucketWrite"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]

    resources = [
      "${var.logs_bucket_arn}/*"
    ]
  }
}

resource "aws_iam_policy" "glue_s3_access" {
  name        = var.policy_name
  description = "Allows AWS Glue jobs to access BAIP S3 buckets."
  policy      = data.aws_iam_policy_document.glue_s3_access.json

  tags = merge(
    var.tags,
    {
      Name = var.policy_name
    }
  )
}

resource "aws_iam_role_policy_attachment" "aws_glue_service_role" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "glue_s3_access" {
  role       = aws_iam_role.this.name
  policy_arn = aws_iam_policy.glue_s3_access.arn
}