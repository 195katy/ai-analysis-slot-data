import csv
import io
import pathlib

import boto3
from botocore.exceptions import ClientError

from app.config import (
    AWS_REGION,
    LOCAL_DATA_DIR,
    S3_BUCKET,
    S3_CSV_KEY,
    STORAGE_TYPE,
)

CSV_COLUMNS = [
    "date", "machine_number", "diff_medals", "games",
    "payout_rate", "bb", "rb", "combined_rate", "bb_rate", "rb_rate",
]

HEADER_LINE = ",".join(CSV_COLUMNS) + "\n"


# --- ローカルストレージ ---

def _local_csv_path() -> pathlib.Path:
    d = pathlib.Path(LOCAL_DATA_DIR)
    d.mkdir(exist_ok=True)
    return d / "data.csv"


def _local_read() -> str:
    path = _local_csv_path()
    if path.exists():
        return path.read_text(encoding="utf-8")
    return HEADER_LINE


def _local_write(content: str) -> None:
    _local_csv_path().write_text(content, encoding="utf-8")


# --- S3ストレージ ---

def _s3_client():
    return boto3.client("s3", region_name=AWS_REGION)


def _s3_read() -> str:
    try:
        resp = _s3_client().get_object(Bucket=S3_BUCKET, Key=S3_CSV_KEY)
        return resp["Body"].read().decode("utf-8")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return HEADER_LINE
        raise


def _s3_write(content: str) -> None:
    _s3_client().put_object(
        Bucket=S3_BUCKET,
        Key=S3_CSV_KEY,
        Body=content.encode("utf-8"),
        ContentType="text/csv",
    )


# --- 共通インターフェース ---

def _read_existing_csv() -> str:
    if STORAGE_TYPE == "s3":
        return _s3_read()
    return _local_read()


def _write_csv(content: str) -> None:
    if STORAGE_TYPE == "s3":
        _s3_write(content)
    else:
        _local_write(content)


def append_data(date: str, rows: list[dict]) -> int:
    # 既存データを読み込み
    existing = _read_existing_csv()
    reader = csv.DictReader(io.StringIO(existing))
    all_rows = list(reader)

    # 新しいデータを追加
    for row in rows:
        all_rows.append({k: {"date": date, **row}.get(k, "") for k in CSV_COLUMNS})

    # 日付でソート
    all_rows.sort(key=lambda r: r.get("date", ""))

    # 書き出し
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(all_rows)

    _write_csv(buf.getvalue())
    return len(rows)


def read_all_data() -> str:
    return _read_existing_csv()
