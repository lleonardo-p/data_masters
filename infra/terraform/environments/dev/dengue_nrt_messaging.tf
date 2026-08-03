locals {
  dengue_nrt_queue_name        = "${var.project_name}-${var.environment}-dengue-triage"
  dengue_nrt_dlq_name          = "${local.dengue_nrt_queue_name}-dlq"
  dengue_nrt_alerts_topic_name = "${var.project_name}-${var.environment}-dengue-nrt-alerts"
}

resource "aws_sqs_queue" "dengue_nrt_dlq" {
  name = local.dengue_nrt_dlq_name

  message_retention_seconds  = 1209600
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 180

  tags = {
    purpose = "dengue-nrt-dead-letter-queue"
    layer   = "messaging"
  }
}

resource "aws_sqs_queue" "dengue_nrt" {
  name = local.dengue_nrt_queue_name

  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 180

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dengue_nrt_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    purpose = "dengue-nrt-triage-events"
    layer   = "messaging"
  }
}

resource "aws_sqs_queue_redrive_allow_policy" "dengue_nrt_dlq" {
  queue_url = aws_sqs_queue.dengue_nrt_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns = [
      aws_sqs_queue.dengue_nrt.arn
    ]
  })
}

data "aws_iam_policy_document" "dengue_nrt_queue" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions   = ["sqs:*"]
    resources = [aws_sqs_queue.dengue_nrt.arn]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_sqs_queue_policy" "dengue_nrt" {
  queue_url = aws_sqs_queue.dengue_nrt.id
  policy    = data.aws_iam_policy_document.dengue_nrt_queue.json
}

data "aws_iam_policy_document" "dengue_nrt_dlq" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions   = ["sqs:*"]
    resources = [aws_sqs_queue.dengue_nrt_dlq.arn]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_sqs_queue_policy" "dengue_nrt_dlq" {
  queue_url = aws_sqs_queue.dengue_nrt_dlq.id
  policy    = data.aws_iam_policy_document.dengue_nrt_dlq.json
}

data "aws_iam_policy_document" "dengue_nrt_producer" {
  statement {
    sid    = "PublishSyntheticTriageEvents"
    effect = "Allow"

    actions = [
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:SendMessage"
    ]

    resources = [aws_sqs_queue.dengue_nrt.arn]
  }
}

resource "aws_iam_policy" "dengue_nrt_producer" {
  name        = "${local.dengue_nrt_queue_name}-producer-policy"
  description = "Allows the local hospital simulator to publish synthetic triage events."
  policy      = data.aws_iam_policy_document.dengue_nrt_producer.json

  tags = {
    purpose = "dengue-nrt-producer-access"
  }
}

resource "aws_sns_topic" "dengue_nrt_alerts" {
  name = local.dengue_nrt_alerts_topic_name

  tags = {
    purpose = "dengue-nrt-alerts"
  }
}

resource "aws_cloudwatch_metric_alarm" "dengue_nrt_dlq_has_messages" {
  alarm_name          = "${local.dengue_nrt_dlq_name}-has-messages"
  alarm_description   = "At least one dengue NRT triage event reached the DLQ."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dengue_nrt_dlq.name
  }

  alarm_actions = [aws_sns_topic.dengue_nrt_alerts.arn]

  tags = {
    purpose = "dengue-nrt-dlq-alert"
  }
}

resource "aws_cloudwatch_metric_alarm" "dengue_nrt_queue_backlog" {
  alarm_name          = "${local.dengue_nrt_queue_name}-backlog"
  alarm_description   = "Dengue NRT main queue has at least 1,000 visible events."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 1000
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dengue_nrt.name
  }

  alarm_actions = [aws_sns_topic.dengue_nrt_alerts.arn]

  tags = {
    purpose = "dengue-nrt-backlog-alert"
  }
}
