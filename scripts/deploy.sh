#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT/terraform"

# Terraform出力から各種情報を取得
ECR_URL=$(terraform output -raw ecr_repository_url)
FUNCTION_NAME=$(terraform output -raw lambda_function_name)
FRONTEND_API_URL=$(terraform output -raw frontend_url 2>/dev/null || echo "")
REGION=$(echo "$ECR_URL" | cut -d. -f4)
ACCOUNT_ID=$(echo "$ECR_URL" | cut -d. -f1)

echo "=== ECR ログイン ==="
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

echo "=== Docker イメージビルド ==="
docker build -f "$PROJECT_ROOT/Dockerfile" -t "$ECR_URL:latest" "$PROJECT_ROOT"

echo "=== ECR プッシュ ==="
docker push "$ECR_URL:latest"

echo "=== Lambda 更新 ==="
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --image-uri "$ECR_URL:latest" \
  --region "$REGION" > /dev/null

echo "=== フロントエンドHTML デプロイ ==="
if [ -n "$FRONTEND_API_URL" ] && [ -f "$PROJECT_ROOT/static/index.html" ]; then
  API_URL="${FRONTEND_API_URL%/}"
  sed "s|var API_URL = window.API_URL .*|var API_URL = '${API_URL}';|" \
    "$PROJECT_ROOT/static/index.html" > /tmp/index.html
  aws s3 cp /tmp/index.html "s3://${FUNCTION_NAME}-frontend/index.html" \
    --content-type "text/html; charset=utf-8" --region "$REGION"
  rm -f /tmp/index.html
  echo "  フロント: http://${FUNCTION_NAME}-frontend.s3-website-$REGION.amazonaws.com/index.html"
fi

echo ""
echo "=== デプロイ完了 ==="
echo "  ECR: $ECR_URL:latest"
echo "  Lambda: $FUNCTION_NAME"
