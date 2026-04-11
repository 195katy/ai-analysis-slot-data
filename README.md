# Slot Data Analyzer

スロットデータの整形・蓄積・AI分析ツール。

コピペした雑なスロットデータをAI（AWS Bedrock Claude）で構造化し、CSVとしてS3に蓄積。蓄積データに対してAI分析を行える。

## アーキテクチャ

```
ブラウザ → S3 (静的ウェブサイト) ... フロントエンド配信
         → Lambda Function URL (frontend) ... API
              ├── save, history → 直接処理 (S3 CSV読み書き)
              └── parse, analyze → Lambda (worker) を非同期invoke
                                    → Bedrock Claude
                                    → 結果をS3 (jobs/) に保存
         → ポーリング (GET /api/result) ... 結果取得
```

## AWSリソース

| リソース | 用途 |
|---------|------|
| S3 (slot-data-accumulation) | データCSV蓄積 + ジョブ結果一時保存 |
| S3 (slot-data-analysis-frontend) | フロントエンドHTML配信 |
| ECR | Dockerイメージ保管 |
| Lambda (slot-data-analysis) | フロントエンドAPI |
| Lambda (slot-data-analysis-worker) | Bedrock処理ワーカー |
| IAM Role | Lambda実行ロール |

## デプロイ

### 前提

- IAMユーザーに `docs/iam-deploy-policy.json` のポリシーをアタッチ済み
- `~/.aws/credentials` にアクセスキーを設定済み
- Docker Desktop がインストール済み

### terraformコンテナの起動

```bash
cd .devcontainer/terraform && docker compose up -d --build
```

### 初回デプロイ

```bash
# 1. インフラ作成（Lambda はイメージ不在で失敗する）
docker exec terraform-terraform-1 terraform -chdir=/workspace/terraform apply -auto-approve

# 2. イメージビルド → push → Lambda作成 → フロントデプロイ
docker exec terraform-terraform-1 bash /workspace/scripts/deploy.sh
```

### 2回目以降

```bash
docker exec terraform-terraform-1 bash /workspace/scripts/deploy.sh
```

### リソース削除

```bash
docker exec terraform-terraform-1 aws s3 rm s3://slot-data-analysis-frontend --recursive --region ap-northeast-1
docker exec terraform-terraform-1 aws s3 rm s3://slot-data-accumulation --recursive --region ap-northeast-1
docker exec terraform-terraform-1 terraform -chdir=/workspace/terraform destroy -auto-approve
```
