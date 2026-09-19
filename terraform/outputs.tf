output "ecr_repository_url" {
  description = "ECRリポジトリURL"
  value       = aws_ecr_repository.app.repository_url
}

output "lambda_function_name" {
  description = "Lambda関数名"
  value       = aws_lambda_function.app.function_name
}

output "frontend_url" {
  description = "API URL"
  value       = aws_lambda_function_url.app.function_url
}

output "frontend_website_url" {
  description = "フロントエンド画面URL"
  value       = "http://${aws_s3_bucket.frontend.bucket}.s3-website-${data.aws_region.current.name}.amazonaws.com/index.html"
}
