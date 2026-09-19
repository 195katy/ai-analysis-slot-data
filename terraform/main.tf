data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  project_name = "slot-data-analysis"
  model_id     = "jp.anthropic.claude-haiku-4-5-20251001-v1:0"
}

# ------------------------------------------------------------
# S3 バケット（抽出データ蓄積用・非公開）
# ------------------------------------------------------------
resource "aws_s3_bucket" "data" {
  bucket = "${local.project_name}-data"
}

# ------------------------------------------------------------
# ECR リポジトリ
# ------------------------------------------------------------
resource "aws_ecr_repository" "app" {
  name         = local.project_name
  force_delete = true
}

# ------------------------------------------------------------
# IAM ロール
# ------------------------------------------------------------
resource "aws_iam_role" "lambda" {
  name = "${local.project_name}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = "${local.project_name}-lambda"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.data.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.data.arn}/*"
      },
    ]
  })
}

# ------------------------------------------------------------
# Lambda 関数 — 画像抽出API（同期処理）
# ------------------------------------------------------------
resource "aws_lambda_function" "app" {
  function_name = local.project_name
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"
  image_config {
    command = ["app.handler.handler"]
  }
  timeout     = 60
  memory_size = 256

  environment {
    variables = {
      BEDROCK_MODEL_ID = local.model_id
      S3_BUCKET        = aws_s3_bucket.data.id
    }
  }

  depends_on = [aws_iam_role_policy.lambda]
}

resource "aws_lambda_function_url" "app" {
  function_name      = aws_lambda_function.app.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST"]
    allow_headers = ["content-type"]
    max_age       = 3600
  }
}

# ------------------------------------------------------------
# S3 静的ウェブサイトホスティング（フロントエンド）
# ------------------------------------------------------------
resource "aws_s3_bucket" "frontend" {
  bucket = "${local.project_name}-frontend"
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}
