from __future__ import annotations

from collections import Counter
from typing import Any


def top_pain_points_from_results(
    results: list[dict[str, Any]],
    *,
    top_k: int = 3,
    include_neutral: bool = False,
) -> list[dict[str, Any]]:
    """
    Week 7 support utility:
    aggregate high-frequency pain points from sentiment-analysis outputs.
    """
    counter: Counter[str] = Counter()
    for row in results:
        sentiment = str(row.get("sentiment", "")).lower()
        if sentiment != "negative" and not (include_neutral and sentiment == "neutral"):
            continue
        for pp in row.get("pain_points", []) or []:
            key = str(pp).strip()
            if key:
                counter[key] += 1

    out = []
    for item, cnt in counter.most_common(max(1, top_k)):
        out.append({"pain_point": item, "count": cnt})
    return out
