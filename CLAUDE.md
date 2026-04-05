# CLAUDE.md

## プロジェクト概要

スロットデータの整形・蓄積・AI分析を行うWebアプリ。フロントとAPIは分離構成。

## 技術スタック

- Backend: Flask (Python 3.12)
- AI: AWS Bedrock (Claude)
- パッケージ管理: uv
- 開発環境: DevContainer
- 本番: Lambda (Function URL) + S3

## ローカル開発の起動方法

```bash
# API (ポート8000)
uv run python -m app.main

# フロント (ポート3000)
cd static && python -m http.server 3000
```

## 設計方針

- config.pyにデフォルト値を持たせない。全て環境変数必須
- ローカルの環境変数は`.devcontainer/devcontainer.json`、本番は`Dockerfile`で管理
- ストレージはSTORAGE_TYPEでlocal/s3を切り替え。コードの分岐はstorage.pyに閉じている
- フロントとAPIは別プロセス。ローカルではpython http.server、本番ではS3でフロント配信
- Lambda移行時にapp/main.pyの変更は不要。handler.py (awsgi2) が変換する

## ファイル構成

- `app/main.py` — Flaskルーティング。エンドポイント定義のみ
- `app/bedrock.py` — Bedrock呼び出し。parse_slot_data / analyze_data
- `app/storage.py` — CSV読み書き。ローカル/S3の切り替えロジック
- `app/config.py` — 環境変数の読み込みだけ
- `app/handler.py` — Lambda用。awsgi2でFlask→Lambdaイベント変換
- `static/index.html` — フロントエンド。API_BASEでAPI接続先を指定
- `Dockerfile` — Lambda用コンテナイメージ + 本番環境変数
- `.devcontainer/devcontainer.json` — ローカル開発環境 + ローカル環境変数
