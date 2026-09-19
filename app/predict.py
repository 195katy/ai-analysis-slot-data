"""傾向データ(2軸)に基づく決定的な翌日予測ロジック。AIの自由判断は使わない。"""

import re
from datetime import datetime

DECAY_RATE = 0.5  # 1日古くなるごとに重みが半分になる
CONFIDENCE_THRESHOLD = 4
SCORE_MARGIN = 0.5  # 最高/最低スコアからこの範囲内を「本命」とみなす


def predict_next_day(rows: list[dict], tendency_items: list[dict]) -> list[dict]:
    axes = {item["key"]: item.get("level", 3) for item in tendency_items}
    sueoki_age = axes.get("sueoki_age", 3)
    layout = axes.get("layout", 3)

    if sueoki_age == 3:
        return []  # 据え置き/上げ下げのどちらに寄るか判断できないため予測しない

    scores = _weighted_scores(rows)
    if not scores:
        return []

    direction = "high" if sueoki_age > 3 else "low"
    axis_strength = abs(sueoki_age - 3)  # 1 or 2
    base_confidence = 3 + axis_strength  # 4 or 5

    if direction == "high":
        top = max(scores.values())
        base = [m for m, s in scores.items() if s >= top - SCORE_MARGIN]
        base_reason = "直近の設定が高く、据え置き傾向が強い店舗のため本命"
    else:
        bottom = min(scores.values())
        base = [m for m, s in scores.items() if s <= bottom + SCORE_MARGIN]
        base_reason = "直近の設定が低く、上げ下げ傾向が強い店舗のため本命"

    candidates = {m: (base_confidence, base_reason) for m in base}

    if layout != 3:
        layout_strength = abs(layout - 3)
        neighbor_confidence = base_confidence - (3 - layout_strength)  # layout=5→-1, layout=4→-2
        if layout > 3:  # 並び傾向: 隣接台番号も候補に追加
            all_machines = sorted(scores.keys(), key=_machine_sort_key)
            for m in base:
                for neighbor in _adjacent(m, all_machines):
                    if neighbor not in candidates:
                        candidates[neighbor] = (neighbor_confidence, "並び傾向により本命台の隣接台として候補")

    results = [
        {"machine_number": m, "confidence": conf, "reason": reason}
        for m, (conf, reason) in candidates.items()
        if conf >= CONFIDENCE_THRESHOLD
    ]
    results.sort(key=lambda x: (-x["confidence"], _machine_sort_key(x["machine_number"])))
    return results


def _weighted_scores(rows: list[dict]) -> dict[str, float]:
    dates = sorted({r["date"] for r in rows if r.get("date")})
    if not dates:
        return {}
    latest_date = datetime.strptime(dates[-1], "%Y-%m-%d")

    weighted_sum: dict[str, float] = {}
    weight_sum: dict[str, float] = {}
    for row in rows:
        value = _to_number(row.get("estimated_setting"))
        date_str = row.get("date")
        machine = row.get("machine_number")
        if value is None or not date_str or not machine:
            continue
        days_ago = (latest_date - datetime.strptime(date_str, "%Y-%m-%d")).days
        weight = DECAY_RATE ** days_ago
        weighted_sum[machine] = weighted_sum.get(machine, 0.0) + weight * value
        weight_sum[machine] = weight_sum.get(machine, 0.0) + weight

    return {m: weighted_sum[m] / weight_sum[m] for m in weighted_sum if weight_sum[m] > 0}


def _to_number(value) -> float | None:
    if value is None or value == "":
        return None
    m = re.search(r"\d+", str(value))
    return float(m.group()) if m else None


def _machine_sort_key(machine_number: str):
    return (len(machine_number), machine_number)


def _adjacent(machine_number: str, all_machines: list[str]) -> list[str]:
    try:
        n = int(machine_number)
    except ValueError:
        return []
    candidates = {str(n - 1), str(n + 1)}
    return [m for m in all_machines if m in candidates]
