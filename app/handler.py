"""AWS Lambda ハンドラー — スクリーンショット画像からスロットデータを抽出するだけのAPI"""

import base64
import json

from app.bedrock import analyze_tendency, estimate_settings, parse_slot_image
from app.predict import predict_next_day
from app.storage import append_data, load_tendency, read_all_data, read_rows_for, save_tendency


def _response(status_code: int, body, content_type: str = "application/json") -> dict:
    if content_type == "application/json":
        body = json.dumps(body, ensure_ascii=False)
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": content_type},
        "body": body,
    }


def _parse_body(event) -> dict:
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
    elif method == "GET" and path == "/api/history":
        return _handle_history()
    elif method == "GET" and path == "/api/tendency":
        return _handle_get_tendency(event)
    elif method == "POST" and path == "/api/tendency":
        return _handle_update_tendency(event)
    elif method == "POST" and path == "/api/predict":
        return _handle_predict(event)
    else:
        return _response(404, {"error": f"Not found: {method} {path}"})


def _handle_parse(event) -> dict:
    data = _parse_body(event)
    try:
        parsed = parse_slot_image(data["image_base64"], data.get("media_type", "image/jpeg"))
    except Exception as e:
        return _response(500, {"error": str(e)})
    try:
        settings_by_machine = estimate_settings(parsed)
        for row in parsed:
            row["estimated_setting"] = settings_by_machine.get(str(row.get("machine_number")), "")
    except Exception as e:
        print(f"設定推定に失敗しました: {e}")
    try:
        append_data(parsed, data["date"], data["store_name"], data["model_name"])
    except Exception as e:
        print(f"CSVへの保存に失敗しました: {e}")
    return _response(200, {"data": parsed})


def _handle_history() -> dict:
    return _response(200, read_all_data(), content_type="text/csv")


def _handle_get_tendency(event) -> dict:
    params = event.get("queryStringParameters") or {}
    store_name = params.get("store_name", "")
    model_name = params.get("model_name", "")
    if not store_name or not model_name:
        return _response(400, {"error": "store_name and model_name are required"})
    tendency = load_tendency(store_name, model_name)
    return _response(200, {"tendency": tendency})


def _handle_update_tendency(event) -> dict:
    data = _parse_body(event)
    store_name = data["store_name"]
    model_name = data["model_name"]
    rows = read_rows_for(store_name, model_name)
    if not rows:
        return _response(400, {"error": "この店舗・機種の蓄積データがありません"})
    try:
        items = analyze_tendency(store_name, model_name, rows)
    except Exception as e:
        return _response(500, {"error": str(e)})
    save_tendency(store_name, model_name, items, len(rows))
    return _response(200, {"tendency": load_tendency(store_name, model_name)})


def _handle_predict(event) -> dict:
    data = _parse_body(event)
    store_name = data["store_name"]
    model_name = data["model_name"]
    rows = read_rows_for(store_name, model_name)
    if not rows:
        return _response(400, {"error": "この店舗・機種の蓄積データがありません"})
    tendency = load_tendency(store_name, model_name)
    if not tendency:
        return _response(400, {"error": "先に「傾向を更新する」を実行してください"})
    try:
        result = predict_next_day(rows, tendency["items"])
    except ValueError as e:
        return _response(400, {"error": str(e)})
    return _response(200, result)
