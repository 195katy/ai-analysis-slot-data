import csv
import io

import boto3
from botocore.exceptions import ClientError

from app.config import AWS_REGION, S3_BUCKET, S3_CSV_KEY

_s3 = boto3.client("s3", region_name=AWS_REGION)

CSV_COLUMNS = [
    "date", "machine_number", "diff_medals", "games",
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


def append_data(date: str, rows: list[dict]) -> int:
    existing = _read_csv()
    reader = csv.DictReader(io.StringIO(existing))
    all_rows = list(reader)

    for row in rows:
        all_rows.append({k: {"date": date, **row}.get(k, "") for k in CSV_COLUMNS})

    all_rows.sort(key=lambda r: r.get("date", ""))

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(all_rows)

    _write_csv(buf.getvalue())
    return len(rows)


def read_all_data() -> str:
    return _read_csv()
