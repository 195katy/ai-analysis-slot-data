import json

import boto3

from app.config import AWS_REGION, BEDROCK_MODEL_ID

_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def invoke(system: str, user_message: str) -> str:
    """Bedrock Claude を呼び出して応答テキストを返す"""
    response = _client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "system": system,
                "messages": [{"role": "user", "content": user_message}],
            }
        ),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def parse_slot_data(raw_text: str) -> list[dict]:
    """雑なテキストを構造化JSONに変換する"""
    system = (
        "あなたはスロットデータの整形アシスタントです。"
        "ユーザーが貼り付けたスロット台のデータを解析し、JSON配列として返してください。"
        "各要素は以下のキーを持つオブジェクトにしてください: "
        "machine_number(台番号,int), diff_medals(差枚,int), games(G数,int), "
        "payout_rate(出率,float,例102.2), bb(BB回数,int), rb(RB回数,int), "
        "combined_rate(合成確率の分母,float), bb_rate(BB確率の分母,float), rb_rate(RB確率の分母,float)。"
        "機種名がある場合は model_name キーとして各要素に含めてください。"
        "JSON配列のみを返し、他の説明は不要です。```json などのマークダウン記法も不要です。"
    )
    text = invoke(system, raw_text)
    return json.loads(text)


def analyze_data(data: list[dict], question: str = "") -> str:
    """整形済みデータをAIに分析させる"""
    system = (
        "あなたはスロットデータの分析エキスパートです。"
        "与えられたデータを分析し、傾向・注目台・設定推測などの洞察を提供してください。"
        "回答は日本語でMarkdown形式で返してください。"
    )
    user_msg = f"以下のスロットデータを分析してください。\n\nデータ:\n{json.dumps(data, ensure_ascii=False)}"
    if question:
        user_msg += f"\n\n追加の質問: {question}"
    return invoke(system, user_msg)
