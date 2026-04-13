from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from config import get_llm_provider
from customer_service import generate_customer_service_reply_as_dict
from llm_factory import get_llm_service


def _read_text_arg(text_arg: str | None, file_path: str | None) -> str:
    if file_path:
        p = Path(file_path)
        if not p.is_file():
            raise SystemExit(f"file not found: {p}")
        return p.read_text(encoding="utf-8")
    if text_arg is not None:
        return text_arg
    return sys.stdin.read()


def main() -> None:
    provider = get_llm_provider()
    parser = argparse.ArgumentParser(
        description=(
            f"LLM backend CLI ({provider}). "
            "task=analyze for sentiment analysis, task=reply for customer-service reply generation."
        )
    )
    parser.add_argument("text", nargs="?", default=None, help="review text; if omitted, read from stdin")
    parser.add_argument("--file", "-f", metavar="PATH", help="read review text from UTF-8 file")
    parser.add_argument(
        "--task",
        choices=["analyze", "reply"],
        default="analyze",
        help="analyze: sentiment analysis; reply: customer-service reply",
    )
    parser.add_argument("--summary-language", default="zh", help="summary language for analyze task: zh/en")
    parser.add_argument("--reply-language", default="zh", help="reply language for reply task: zh/en")
    parser.add_argument("--merchant-rules", default="", help="merchant rule text used in reply task")
    parser.add_argument("--merchant-rules-file", default=None, help="UTF-8 file path for merchant rules")
    parser.add_argument("--sentiment", default=None, help="optional sentiment hint for reply task")
    parser.add_argument("--pain-points", default="", help="optional pain points, comma-separated")
    parser.add_argument("--style-hint", default=None, help="optional style hint for reply tone")

    args = parser.parse_args()

    if args.file and args.text is not None:
        raise SystemExit("use either positional text or --file, not both")

    review_text = _read_text_arg(args.text, args.file).strip()
    if not review_text:
        raise SystemExit("empty input text")

    try:
        if args.task == "analyze":
            service = get_llm_service()
            result = service.analyze_review_as_dict(
                review_text,
                summary_language=args.summary_language,
            )
        else:
            rules_text = _read_text_arg(None, args.merchant_rules_file) if args.merchant_rules_file else args.merchant_rules
            pain_points = [x.strip() for x in (args.pain_points or "").split(",") if x.strip()]
            result = generate_customer_service_reply_as_dict(
                review_text=review_text,
                merchant_rules=rules_text,
                sentiment=args.sentiment,
                pain_points=pain_points or None,
                style_hint=args.style_hint,
                reply_language=args.reply_language,
            )

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        raise SystemExit(f"[{provider.upper()} ERROR] {type(exc).__name__}: {exc}") from exc


if __name__ == "__main__":
    main()
