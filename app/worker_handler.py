"""AWS Lambda ハンドラー — Bedrock処理ワーカー

frontendから非同期invokeされ、結果をS3に保存。
"""

import json
import os

import boto3

from app.bedrock import analyze_data, parse_slot_data

s3 = boto3.client("s3")
S3_BUCKET = os.environ.get("S3_BUCKET", "")


def handler(event, context):
    action = event.get("action")
    job_id = event.get("job_id")

    if action == "parse":
        parsed = parse_slot_data(event["raw_text"])
        result = {"status": "done", "data": parsed}
    elif action == "analyze":
        analysis = analyze_data(event["data"], event.get("question", ""))
        result = {"status": "done", "analysis": analysis}
    else:
        result = {"status": "error", "error": f"Unknown action: {action}"}

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"jobs/{job_id}.json",
        Body=json.dumps(result, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )
