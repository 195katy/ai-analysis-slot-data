from flask import Flask, jsonify, request
from flask_cors import CORS

from app.bedrock import analyze_data, parse_slot_data
from app.storage import append_data, read_all_data

app = Flask(__name__)
CORS(app)


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/api/parse", methods=["POST"])
def api_parse():
    """雑なテキストを構造化データに変換"""
    raw_text = request.json["raw_text"]
    return jsonify(data=parse_slot_data(raw_text))


@app.route("/api/save", methods=["POST"])
def api_save():
    """整形済みデータをS3のCSVに追記"""
    date = request.json["date"]
    data = request.json["data"]
    count = append_data(date, data)
    return jsonify(saved=count)


@app.route("/api/history")
def api_history():
    """S3から蓄積データを取得"""
    return read_all_data(), 200, {"Content-Type": "text/csv"}


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """整形済みデータをAI分析"""
    data = request.json["data"]
    question = request.json.get("question", "")
    return jsonify(analysis=analyze_data(data, question))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
