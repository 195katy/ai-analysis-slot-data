"""AWS Lambda ハンドラー — フロントエンドAPI（Function URL）

軽い処理は直接実行、重い処理（Bedrock呼び出し）はworkerに非同期委譲。
"""

import json
import os
import uuid

import boto3

from app.storage import append_data, read_all_data

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")

S3_BUCKET = os.environ.get("S3_BUCKET", "")
WORKER_FUNCTION_NAME = os.environ.get("WORKER_FUNCTION_NAME", "")


def _response(status_code: int, body, content_type: str = "application/json") -> dict:
    headers = {"Content-Type": content_type}
    if content_type == "application/json" and isinstance(body, dict):
        body = json.dumps(body, ensure_ascii=False)
    return {"statusCode": status_code, "headers": headers, "body": body}


def _parse_body(event) -> dict:
    import base64
    body = event.get("body", "")
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(body).decode("utf-8")
    return json.loads(body)


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")

    if method == "OPTIONS":
        return _response(200, {})

    if method == "GET" and path == "/health":
        return _response(200, {"status": "ok"})
    elif method == "POST" and path == "/api/parse":
        return _handle_parse(event)
    elif method == "POST" and path == "/api/save":
        return _handle_save(event)
    elif method == "GET" and path == "/api/history":
        return _handle_history()
    elif method == "POST" and path == "/api/analyze":
        return _handle_analyze(event)
    elif method == "GET" and path == "/api/result":
        return _handle_result(event)
    else:
        return _response(404, {"error": f"Not found: {method} {path}"})


def _handle_parse(event) -> dict:
    """Bedrock整形をworkerに非同期委譲"""
    data = _parse_body(event)
    job_id = str(uuid.uuid4())

    lambda_client.invoke(
        FunctionName=WORKER_FUNCTION_NAME,
        InvocationType="Event",
        Payload=json.dumps({
            "action": "parse",
            "job_id": job_id,
            "raw_text": data["raw_text"],
        }).encode("utf-8"),
    )

    return _response(202, {"job_id": job_id})


def _handle_save(event) -> dict:
    data = _parse_body(event)
    count = append_data(data["date"], data["data"])
    return _response(200, {"saved": count})


def _handle_history() -> dict:
    csv_data = read_all_data()
    return _response(200, csv_data, content_type="text/csv")


def _handle_analyze(event) -> dict:
    """Bedrock分析をworkerに非同期委譲"""
    data = _parse_body(event)
    job_id = str(uuid.uuid4())

    lambda_client.invoke(
        FunctionName=WORKER_FUNCTION_NAME,
        InvocationType="Event",
        Payload=json.dumps({
            "action": "analyze",
            "job_id": job_id,
            "data": data["data"],
            "question": data.get("question", ""),
        }).encode("utf-8"),
    )

    return _response(202, {"job_id": job_id})


def _handle_result(event) -> dict:
    """ジョブ結果をS3から取得（ポーリング用）"""
    params = event.get("queryStringParameters") or {}
    job_id = params.get("job_id", "")

    if not job_id:
        return _response(400, {"error": "job_id is required"})

    from botocore.exceptions import ClientError
    try:
        resp = s3.get_object(Bucket=S3_BUCKET, Key=f"jobs/{job_id}.json")
        result = json.loads(resp["Body"].read().decode("utf-8"))
        s3.delete_object(Bucket=S3_BUCKET, Key=f"jobs/{job_id}.json")
        return _response(200, result)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return _response(200, {"status": "processing"})
        raise
