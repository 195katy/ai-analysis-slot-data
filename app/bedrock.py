import json

import boto3

from app.config import AWS_REGION, BEDROCK_MODEL_ID

_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def invoke(system: str, user_message, temperature: float = 1.0) -> str:
    response = _client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 16384,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user_message}],
            }
        ),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def parse_slot_image(image_b64: str, media_type: str = "image/jpeg") -> list[dict]:
    system = (
        "あなたはスロットデータの整形アシスタントです。"
        "ユーザーが送信したスロット台データ一覧のスクリーンショット画像を解析し、JSON配列として返してください。"
        "画像内の表から各データ行を読み取り、以下のキーを持つオブジェクトにしてください: "
        "machine_number(台番,int), diff_medals(差枚,int), games(G数,int), "
        "payout_rate(出率,float,%記号は外す,例102.2), bb(BB回数,int), rb(RB回数,int), "
        "combined_rate(合成確率の分母,float), bb_rate(BB確率の分母,float), rb_rate(RB確率の分母,float)。"
        "画像に存在しないキーは省略してください。ヘッダー行・広告・ナビゲーション部分は無視し、データ行のみ抽出してください。"
        "JSON配列のみを返し、他の説明は不要です。```json などのマークダウン記法も不要です。"
    )
    user_message = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_b64,
            },
        },
        {
            "type": "text",
            "text": "この画像のスロットデータ一覧表を解析してJSON配列で返してください。",
        },
    ]
    text = invoke(system, user_message)
    return _extract_json_array(text)


def estimate_settings(rows: list[dict]) -> dict:
    system = (
        "あなたはスロット(パチスロ)の設定推測エキスパートです。"
        "与えられた台ごとのデータ(差枚, G数, 出率, BB回数, RB回数, 合成確率, BB確率, RB確率の分母)を基に、"
        "各台の推定設定を判定してください。"
        "出率やBB・RB確率が公表されている機種の一般的な設定判別要素(出率の高さ、BB/RB比率など)を踏まえて判断してください。"
        "各台についてmachine_number(入力と同じ値)とestimated_setting(1〜6の整数。範囲でしか判断できない場合は最も近い整数1つに絞る)を持つ"
        "オブジェクトのJSON配列のみを返してください。他の説明や```json などのマークダウン記法も不要です。"
    )
    user_msg = f"以下は同じ日・同じ機種の台データです。台ごとに推定設定(1〜6の整数)を判定してください。\n\nデータ:\n{json.dumps(rows, ensure_ascii=False)}"
    text = invoke(system, user_msg, temperature=0)
    estimates = _extract_json_array(text)
    return {str(e["machine_number"]): e.get("estimated_setting", "") for e in estimates}


_TENDENCY_AXES = [
    (
        "sueoki_age", "据え置き", "上げ下げ",
        "同じ台に連日高設定を続ける(据え置き)傾向と、差枚が低かった台を翌日以降に高設定にする(上げ下げ)傾向、どちらが強いか",
    ),
    (
        "layout", "並び", "ピン",
        "高設定を並びや列でまとめて入れる(並び)傾向と、単独で入れる(ピン)傾向、どちらが強いか",
    ),
]


def analyze_tendency(store_name: str, model_name: str, rows: list[dict]) -> list[dict]:
    axes_desc = "\n".join(
        f'- key="{k}", pole_left="{left}", pole_right="{right}": {desc}'
        for k, left, right, desc in _TENDENCY_AXES
    )
    system = (
        "あなたはスロット(パチスロ)の店舗傾向分析エキスパートです。"
        "与えられた、ある店舗・ある機種の複数日分の台データ(日付, 曜日, 台番号, 推定設定, 差枚, G数, 出率, BB回数, RB回数など)を基に、"
        "その店舗・機種が持つ恒常的な特徴(この店はどういうお店か)を分析してください。"
        "\n\n"
        "これは「特定の日に何が起きたか」を報告するものではなく、"
        "「このデータから読み取れる、この店舗の一般的な傾向・くせ」を結論として述べるものです。"
        "\n\n"
        f"以下の{len(_TENDENCY_AXES)}つの軸それぞれについて、pole_left寄りかpole_right寄りかを判定してください:\n{axes_desc}\n\n"
        "各軸についてkey, pole_left, pole_right, level, reasonを持つオブジェクトのJSON配列のみを返してください。\n"
        "- key, pole_left, pole_rightは指定された値をそのまま使う\n"
        "- levelは1〜5の整数。1=pole_rightの特徴に強く当てはまる、3=中間もしくは判断できない、5=pole_leftの特徴に強く当てはまる\n"
        "- 例: 「据え置きの傾向が強い」と結論づける場合、pole_left=「据え置き」なのでlevelは5に近い値にする。"
        "逆に「上げ下げの傾向が強い」場合はpole_right=「上げ下げ」なのでlevelは1に近い値にする。reasonの内容とlevelの向きを必ず一致させること\n"
        "- データ不足で判断できない場合はlevelを3にし、reasonに「データ不足」と明記する\n"
        "- reasonはlevelの根拠を1文で。「9月1日」のような具体的な日付、曜日名、複数の台番号の列挙、台数・割合(%)などの数値は一切書かない\n"
        "- 低設定台そのものの分析や、推定設定と出率・差枚の整合性の検証は書かない\n"
        "- JSON配列以外の説明や```json などのマークダウン記法は不要"
    )
    rows_with_weekday = [
        {**row, "weekday": _weekday_ja(row.get("date", ""))}
        for row in rows
    ]
    user_msg = (
        f"店舗「{store_name}」、機種「{model_name}」の過去データです。"
        f"個々の日付の経過ではなく、この店舗の一般化された傾向を分析してください。\n\n"
        f"データ:\n{json.dumps(rows_with_weekday, ensure_ascii=False)}"
    )
    text = invoke(system, user_msg, temperature=0)
    return _extract_json_array(text)


def _weekday_ja(date_str: str) -> str:
    from datetime import datetime
    try:
        return ["月", "火", "水", "木", "金", "土", "日"][datetime.strptime(date_str, "%Y-%m-%d").weekday()]
    except ValueError:
        return ""


def _extract_json_array(text: str) -> list[dict]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # JSON抽出を試みる
        import re
        m = re.search(r"```(?:json)?\s*(\[[\s\S]*\])\s*```", text)
        if m:
            return json.loads(m.group(1))
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
        raise
