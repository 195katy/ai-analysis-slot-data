# CLAUDE.md

## プロジェクト概要

スロットデータの整形・蓄積・AI分析を行うWebアプリ。フロントとAPIは分離構成。

## 技術スタック

- Backend: Python 3.12 (boto3)
- AI: AWS Bedrock (Claude)
- パッケージ管理: uv
- インフラ管理: Terraform (DevContainer内で実行)
- 本番: Lambda (Function URL) + S3

## 設計方針

- config.pyにデフォルト値を持たせない。全て環境変数必須。環境変数はterraform/main.tfで管理（AWS_REGIONはLambdaが自動設定）
- フロントはS3静的ウェブサイトホスティング、APIはLambda Function URL
- 重い処理（Bedrock呼び出し）はworker Lambdaに非同期委譲。フロントはポーリングで結果取得
- 同一Dockerイメージをfrontendとworkerで共有。image_config.commandでハンドラーを切り替え

## ファイル構成

- `app/frontend_handler.py` — Lambda Function URL用。軽い処理は直接、重い処理はworkerに委譲
- `app/worker_handler.py` — Bedrock処理ワーカー。結果をS3 (jobs/) に保存
- `app/bedrock.py` — Bedrock呼び出し。parse_slot_data / analyze_data
- `app/storage.py` — CSV読み書き (S3)
- `app/config.py` — 環境変数の読み込みだけ
- `static/index.html` — フロントエンド。API_URLでAPI接続先を指定
- `Dockerfile` — Lambda用コンテナイメージ
- `.devcontainer/terraform/` — インフラ用DevContainer (Terraform + Docker + AWS CLI)
- `terraform/` — Terraform定義 (main.tf, providers.tf, outputs.tf)
- `scripts/deploy.sh` — ビルド→ECR push→Lambda更新→フロントデプロイの一括スクリプト
- `docs/iam-deploy-policy.json` — デプロイ用IAMポリシー

## デプロイ手順

### 前提

- IAMユーザーに `docs/iam-deploy-policy.json` のポリシーをアタッチ済み
- `~/.aws/credentials` にアクセスキーを設定済み

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
docker exec terraform-terraform-1 aws s3 rm s3://slot-data-accumulation --recursive --region ap-northeast-1

# リソース削除
docker exec terraform-terraform-1 terraform -chdir=/workspace/terraform destroy -auto-approve
```

### 注意事項

- S3バケット削除直後に同名バケットを再作成すると数十分〜1時間かかる場合がある
- deploy.sh はterraformコンテナ内で実行する（Docker-in-Dockerでイメージビルドするため）
