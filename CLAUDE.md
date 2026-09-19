# CLAUDE.md

## プロジェクト概要

スロットデータのスクリーンショット画像をAIで解析し、構造化データとして抽出・表示するだけのシンプルなWebアプリ。

## 技術スタック

- Backend: Python 3.12 (boto3)
- AI: AWS Bedrock (Claude)
- パッケージ管理: uv
- インフラ管理: Terraform (DevContainer内で実行)
- 本番: Lambda (Function URL) + S3

## 設計方針

- config.pyにデフォルト値を持たせない。全て環境変数必須。環境変数はterraform/main.tfで管理（AWS_REGIONはLambdaが自動設定）
- フロントはS3静的ウェブサイトホスティング、APIはLambda Function URL
- Lambdaは1つのみ。画像を受け取りBedrockを同期呼び出しして結果をそのまま返す（非同期委譲・ポーリング・S3への保存は行わない）

## ファイル構成

- `app/handler.py` — Lambda Function URL用ハンドラー。`/api/parse`で画像を受け取りBedrockを同期呼び出しして結果を返す
- `app/bedrock.py` — Bedrock呼び出し。parse_slot_image（スクショ画像からのデータ抽出）
- `app/config.py` — 環境変数の読み込みだけ（AWS_REGION, BEDROCK_MODEL_ID）
- `static/index.html` — フロントエンド。画像アップロード→抽出→結果テーブル表示のみ。API_URLでAPI接続先を指定
- `Dockerfile` — Lambda用コンテナイメージ
- `.devcontainer/app/` — アプリ開発用DevContainer (Python 3.12 + uv)。ローカルの`.venv`は使わずこちらで動作確認する
- `.devcontainer/terraform/` — インフラ用DevContainer (Terraform + Docker + AWS CLI)
- `terraform/` — Terraform定義 (main.tf, providers.tf, outputs.tf)
- `scripts/deploy.sh` — ビルド→ECR push→Lambda更新→フロントデプロイの一括スクリプト
- `docs/iam-deploy-policy.json` — デプロイ用IAMポリシー

## デプロイ手順

### 前提

- IAMユーザーに `docs/iam-deploy-policy.json` のポリシーをアタッチ済み
- `~/.aws/credentials` にアクセスキーを設定済み

### appコンテナの起動（ローカル動作確認用）

```bash
cd .devcontainer/app && docker compose up -d --build
docker exec app-app-1 python -c "import app.handler, app.bedrock"
```

### terraformコンテナの起動

```bash
cd .devcontainer/terraform && docker compose up -d --build
```

### インフラ構築（初回）

```bash
# 1. terraform apply（初回はLambdaがECRイメージ不在で失敗する）
docker exec terraform-terraform-1 terraform -chdir=/workspace/terraform apply -auto-approve

# 2. deploy.sh でイメージpush → Lambda更新 → フロントデプロイを一括実行
docker exec terraform-terraform-1 bash /workspace/scripts/deploy.sh
```

### 2回目以降のデプロイ

```bash
docker exec terraform-terraform-1 bash /workspace/scripts/deploy.sh
```

### リソース削除

```bash
# S3バケット内のファイルを先に削除
docker exec terraform-terraform-1 aws s3 rm s3://slot-data-analysis-frontend --recursive --region ap-northeast-1

# リソース削除
docker exec terraform-terraform-1 terraform -chdir=/workspace/terraform destroy -auto-approve
```

### 注意事項

- S3バケット削除直後に同名バケットを再作成すると数十分〜1時間かかる場合がある
- deploy.sh はterraformコンテナ内で実行する（Docker-in-Dockerでイメージビルドするため）
