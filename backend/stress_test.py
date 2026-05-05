from __future__ import annotations

"""Week 9 backend stress-test runner with resource monitoring."""

import argparse
import asyncio
import csv
import json
import statistics
import time
import tracemalloc
from collections import Counter
from pathlib import Path
from typing import Any

from config import get_llm_max_input_chars
from edge_cases import assess_text_edge_cases, prepare_text_for_llm
from observability import log_backend_event, make_request_id
from prompts import build_system_instruction, build_user_prompt


_DEFAULT_EDGE_CASES = [
    {
        "case_id": "sarcasm_zh_01",
        "category": "sarcasm",
        "text": "真不错啊，等了十天终于收到一个压坏的盒子，体验可真高级。",
    },
    {
        "case_id": "sarcasm_en_01",
        "category": "sarcasm",
        "text": "Great job, the zipper broke before I even used the bag. Thanks for nothing.",
    },
    {"case_id": "emoji_01", "category": "emoji_only", "text": "😡😡😡😡😡"},
    {"case_id": "emoji_02", "category": "emoji_only", "text": "🙂🙂🙂???"},
    {
        "case_id": "gibberish_01",
        "category": "gibberish",
        "text": "asdljkh###@@@%%%%% 999999 qqqqqqqqqq zzzzzzzzzzzzz",
    },
    {
        "case_id": "noise_zh_01",
        "category": "gibberish",
        "text": "包装￥￥￥￥￥物流&&&&&坏坏坏坏坏坏坏坏坏坏",
    },
    {
        "case_id": "rant_01",
        "category": "long_rant",
        "text": "这次购物体验非常差，客服回复慢，包装破损，物流也慢。" * 220,
    },
    {
        "case_id": "hostile_01",
        "category": "hostile",
        "text": "垃圾商家，骗子，马上给我退款，否则我天天来骂。",
    },
    {
        "case_id": "normal_negative_01",
        "category": "normal",
        "text": "商品有明显划痕，包装也破了，希望尽快补发。",
    },
    {
        "case_id": "normal_positive_01",
        "category": "normal",
        "text": "发货快，质量也不错，下次还会回购。",
    },
]


def _load_csv_cases(path: Path, text_column: str | None, limit: int | None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        candidates = [text_column] if text_column else []
        candidates.extend(["review_text", "comment_text", "评论内容", "评价内容", "text", "comment", "review"])
        selected_col = next((col for col in candidates if col and col in reader.fieldnames), reader.fieldnames[0])
        cases: list[dict[str, str]] = []
        for idx, row in enumerate(reader):
            text = str(row.get(selected_col, "") or "").strip()
            if not text:
                continue
            cases.append(
                {
                    "case_id": str(row.get("case_id") or row.get("id") or idx),
                    "category": str(row.get("category") or "uploaded"),
                    "text": text,
                }
            )
            if limit and len(cases) >= limit:
                break
    return cases


def _expand_cases(cases: list[dict[str, str]], repeat: int) -> list[dict[str, str]]:
    expanded: list[dict[str, str]] = []
    for round_idx in range(max(1, repeat)):
        for case in cases:
            item = dict(case)
            item["case_id"] = f"{case['case_id']}#r{round_idx + 1}"
            expanded.append(item)
    return expanded


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((p / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def _offline_analyze(case: dict[str, str], summary_language: str) -> dict[str, Any]:
    started = time.perf_counter()
    text = case["text"]
    assessment = assess_text_edge_cases(text)
    prepared = prepare_text_for_llm(text)
    _ = build_system_instruction(summary_language)
    _ = build_user_prompt(prepared, summary_language=summary_language)

    if assessment.should_handoff:
        sentiment = "neutral"
        confidence = 0.35
    elif any(word in text.lower() or word in text for word in ["差", "坏", "破", "慢", "refund", "broken", "bad"]):
        sentiment = "negative"
        confidence = 0.78
    elif any(word in text.lower() or word in text for word in ["好", "不错", "快", "good", "great"]):
        sentiment = "positive"
        confidence = 0.74
    else:
        sentiment = "neutral"
        confidence = 0.55

    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "status": "ok",
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "sentiment": sentiment,
        "confidence": confidence,
        "edge_flags": assessment.flags,
        "guardrail_action": assessment.guardrail_action,
        "original_length": assessment.original_length,
        "prepared_length": assessment.prepared_length,
    }


async def _live_analyze(
    cases: list[dict[str, str]],
    *,
    provider: str,
    model: str | None,
    summary_language: str,
    concurrency: int,
) -> list[dict[str, Any]]:
    from llm_factory import get_llm_service

    service = get_llm_service(provider=provider, model=model)
    sem = asyncio.Semaphore(max(1, concurrency))

    async def one(case: dict[str, str]) -> dict[str, Any]:
        started = time.perf_counter()
        assessment = assess_text_edge_cases(case["text"])
        async with sem:
            try:
                result = await service.async_analyze_review_as_dict(
                    case["text"],
                    summary_language=summary_language,
                )
                return {
                    "case_id": case["case_id"],
                    "category": case["category"],
                    "status": "ok",
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                    "edge_flags": assessment.flags,
                    "guardrail_action": assessment.guardrail_action,
                    **result,
                }
            except Exception as exc:
                return {
                    "case_id": case["case_id"],
                    "category": case["category"],
                    "status": "error",
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                    "edge_flags": assessment.flags,
                    "guardrail_action": assessment.guardrail_action,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }

    return await asyncio.gather(*(one(case) for case in cases))


def _build_report(results: list[dict[str, Any]], wall_seconds: float, cpu_seconds: float, peak_mb: float) -> dict[str, Any]:
    latencies = [float(r["latency_ms"]) for r in results]
    status_counts = Counter(str(r.get("status", "unknown")) for r in results)
    flag_counts: Counter[str] = Counter()
    for row in results:
        flag_counts.update(row.get("edge_flags") or ["normal"])
    total = len(results)
    return {
        "total_cases": total,
        "status_counts": dict(status_counts),
        "edge_flag_counts": dict(flag_counts),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "p50": round(_percentile(latencies, 50), 2),
            "p95": round(_percentile(latencies, 95), 2),
            "max": round(max(latencies), 2) if latencies else 0.0,
        },
        "resource_usage": {
            "wall_seconds": round(wall_seconds, 3),
            "cpu_seconds": round(cpu_seconds, 3),
            "peak_tracemalloc_mb": round(peak_mb, 3),
            "throughput_per_second": round(total / wall_seconds, 2) if wall_seconds > 0 else 0.0,
            "max_input_chars": get_llm_max_input_chars(),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Week 9 backend stress-test and edge-case runner.")
    parser.add_argument("--file", type=Path, default=None, help="optional CSV file containing stress cases")
    parser.add_argument("--text-column", default=None, help="CSV column containing review text")
    parser.add_argument("--limit", type=int, default=None, help="maximum loaded rows from CSV")
    parser.add_argument("--repeat", type=int, default=1, help="repeat cases to simulate larger batches")
    parser.add_argument("--concurrency", type=int, default=8, help="live-mode concurrency cap")
    parser.add_argument("--summary-language", default="zh", choices=["zh", "en"])
    parser.add_argument("--live", action="store_true", help="call the configured LLM API; default is offline smoke mode")
    parser.add_argument("--provider", default="deepseek", help="provider for live mode")
    parser.add_argument("--model", default=None, help="optional model override for live mode")
    parser.add_argument("--output", type=Path, default=Path("tmp/week9_stress_test_report.json"))
    args = parser.parse_args()

    base_cases = _DEFAULT_EDGE_CASES
    if args.file:
        base_cases = _load_csv_cases(args.file, args.text_column, args.limit)
    cases = _expand_cases(base_cases, args.repeat)
    request_id = make_request_id("stress_test")

    tracemalloc.start()
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    if args.live:
        results = asyncio.run(
            _live_analyze(
                cases,
                provider=args.provider,
                model=args.model,
                summary_language=args.summary_language,
                concurrency=args.concurrency,
            )
        )
    else:
        results = [_offline_analyze(case, args.summary_language) for case in cases]
    wall_seconds = time.perf_counter() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    report = _build_report(results, wall_seconds, cpu_seconds, peak / (1024 * 1024))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log_backend_event(
        operation="stress_test",
        status="ok",
        request_id=request_id,
        latency_ms=int(wall_seconds * 1000),
        attempts=1,
        extra={
            "total_cases": report["total_cases"],
            "status_counts": report["status_counts"],
            "peak_tracemalloc_mb": report["resource_usage"]["peak_tracemalloc_mb"],
            "output": str(args.output),
            "live_mode": args.live,
        },
    )

    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))
    print(f"\nFull report written to: {args.output}")


if __name__ == "__main__":
    main()
