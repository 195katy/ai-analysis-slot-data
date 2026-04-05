# Slot Data Analyzer

スロットデータの整形・蓄積・AI分析ツール。

コピペした雑なスロットデータをAI（AWS Bedrock Claude）で構造化し、CSVとして蓄積。蓄積データに対してAI分析を行える。

## 構成

```
static/index.html  ... フロントエンド（S3配信想定）
app/main.py         ... Flask API
app/bedrock.py      ... Bedrock Claude呼び出し
app/storage.py      ... データ保存（ローカル / S3 切り替え）
app/config.py       ... 環境変数から設定読み込み
app/handler.py      ... Lambda用エントリーポイント（awsgi2）
Dockerfile          ... Lambda用コンテナイメージ
```

## ローカル開発

### 前提

- Docker + VS Code + Dev Containers拡張
- AWS CLI設定済み（`~/.aws/credentials`）
- Bedrockのモデルアクセスが有効

### 起動

1. VS Codeでリポジトリを開き「Reopen in Container」
2. ターミナルを2つ開く

```bash
# ターミナル1: API
uv run python -m app.main

# ターミナル2: フロント
cd static && python -m http.server 3000
```

3. ブラウザで `http://localhost:3000` にアクセス

### 使い方

1. スロットデータをテキストエリアに貼り付けて「整形する」
2. テーブルで確認
3. 日付を選択して「データを保存」（CSVに蓄積）
4. 「AIに分析させる」で分析結果を表示

## 本番環境（AWS）

- フロント: S3 + CloudFront
- API: Lambda (Function URL) + Dockerイメージ
- データ: S3 (CSV)
- AI: Bedrock Claude

## 環境変数

全てconfig.pyで`os.environ`から読み込み。デフォルト値は持たない。

| 変数 | 説明 | ローカル | 本番 |
|------|------|---------|------|
| AWS_REGION | AWSリージョン | us-east-1 | us-east-1 |
| BEDROCK_MODEL_ID | Bedrockモデル | anthropic.claude-3-haiku-20240307-v1:0 | 同左 |
| S3_BUCKET | データ保存先バケット | slot-data-accumulation | 同左 |
| S3_CSV_KEY | CSVファイルパス | data.csv | 同左 |
| STORAGE_TYPE | ストレージ種別 | local | s3 |
| LOCAL_DATA_DIR | ローカル保存先 | local_data | (未使用) |

ローカルの値は `.devcontainer/devcontainer.json`、本番の値は `Dockerfile` で設定。
