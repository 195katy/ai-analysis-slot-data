import csv
import io
import json
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from app.config import AWS_REGION, S3_BUCKET

_s3 = boto3.client("s3", region_name=AWS_REGION)

S3_CSV_KEY = "data.csv"

CSV_COLUMNS = [
    "date", "store_name", "model_name", "machine_number", "estimated_setting", "diff_medals", "games",
    "payout_rate", "bb", "rb", "combined_rate", "bb_rate", "rb_rate",
]

HEADER_LINE = ",".join(CSV_COLUMNS) + "\n"


def _read_csv() -> str:
    try:
        resp = _s3.get_object(Bucket=S3_BUCKET, Key=S3_CSV_KEY)
        return resp["Body"].read().decode("utf-8")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return HEADER_LINE
        raise


def _write_csv(content: str) -> None:
    _s3.put_object(
        Bucket=S3_BUCKET,
        Key=S3_CSV_KEY,
        Body=content.encode("utf-8"),
        ContentType="text/csv",
    )


def append_data(rows: list[dict], date: str, store_name: str, model_name: str) -> int:
    existing = _read_csv()
    reader = csv.DictReader(io.StringIO(existing))
    all_rows = list(reader)

    for row in rows:
        merged = {"date": date, "store_name": store_name, "model_name": model_name, **row}
        all_rows.append({k: merged.get(k, "") for k in CSV_COLUMNS})

    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(all_rows)

    _write_csv(buf.getvalue())
    return len(rows)


def read_all_data() -> str:
    return _read_csv()


def read_rows_for(store_name: str, model_name: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(_read_csv()))
    return [row for row in reader if row["store_name"] == store_name and row["model_name"] == model_name]


def _tendency_key(store_name: str, model_name: str) -> str:
    safe = lambda s: s.replace("/", "_")
    return f"tendency/{safe(store_name)}__{safe(model_name)}.json"


def save_tendency(store_name: str, model_name: str, items: list[dict], based_on_rows: int) -> None:
    key = _tendency_key(store_name, model_name)
    body = {
        "items": items,
        "based_on_rows": based_on_rows,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )


def load_tendency(store_name: str, model_name: str) -> dict | None:
    key = _tendency_key(store_name, model_name)
    try:
        resp = _s3.get_object(Bucket=S3_BUCKET, Key=key)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise
