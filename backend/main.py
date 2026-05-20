from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from api_server import create_app
from config import get_llm_provider
from customer_service import generate_customer_service_reply_as_dict
from knowledge_base import import_knowledge_base, list_knowledge_base_indices, search_knowledge_base_index_file
from llm_factory import get_llm_service
from reporting import (
    build_business_insight_payload,
    build_report_html,
    build_report_markdown,
    build_report_snapshot_svg,
)


def _read_text_arg(text_arg: str | None, file_path: str | None) -> str:
    if file_path:
        p = Path(file_path)
        if not p.is_file():
            raise SystemExit(f"file not found: {p}")
        return p.read_text(encoding="utf-8")
    if text_arg is not None:
        return text_arg
    return sys.stdin.read()


def _load_result_records(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"results file not found: {path}")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            data = data["results"]
        if not isinstance(data, list):
            raise SystemExit("JSON results must be a list or an object with a 'results' list")
        return [dict(item) for item in data if isinstance(item, dict)]

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _write_report_file(payload: dict, output_path: Path) -> None:
    suffix = output_path.suffix.lower()
    if suffix == ".html":
        output_path.write_text(build_report_html(payload), encoding="utf-8")
    elif suffix == ".md":
        output_path.write_text(build_report_markdown(payload), encoding="utf-8")
    elif suffix == ".svg":
        output_path.write_text(build_report_snapshot_svg(payload), encoding="utf-8")
    else:
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_api_server(host: str, port: int) -> None:
    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise SystemExit("uvicorn is not installed. Install fastapi and uvicorn to run the API server.") from exc

    app = create_app()
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    provider = get_llm_provider()
    parser = argparse.ArgumentParser(
        description=(
            f"LLM backend CLI ({provider}). "
            "task=analyze for sentiment analysis, task=reply for customer-service reply generation, "
            "task=kb-import/kb-search/kb-list for knowledge-base workflows, task=serve-api for HTTP serving."
        )
    )
    parser.add_argument("text", nargs="?", default=None, help="review text; if omitted, read from stdin")
    parser.add_argument("--file", "-f", metavar="PATH", help="read review text from UTF-8 file")
    parser.add_argument(
        "--task",
        choices=["analyze", "reply", "report", "kb-import", "kb-search", "kb-list", "serve-api"],
        default="analyze",
        help=(
            "analyze: sentiment analysis; reply: customer-service reply; report: business insight aggregation; "
            "kb-import/search/list: knowledge-base indexing flow; serve-api: run FastAPI service"
        ),
    )
    parser.add_argument("--summary-language", default="zh", help="summary language for analyze task: zh/en")
    parser.add_argument("--reply-language", default="zh", help="reply language for reply task: zh/en")
    parser.add_argument("--merchant-rules", default="", help="merchant rule text used in reply task")
    parser.add_argument("--merchant-rules-file", default=None, help="UTF-8 file path for merchant rules")
    parser.add_argument("--kb-file", default=None, help="optional UTF-8 knowledge-base file for RAG retrieval")
    parser.add_argument("--kb-index-path", default=None, help="optional persisted knowledge-base index JSON path")
    parser.add_argument("--kb-index-id", default=None, help="knowledge-base index id under merchant directory")
    parser.add_argument("--merchant-slug", default="demo-merchant", help="merchant slug for KB workflows / API")
    parser.add_argument("--kb-title", default="Merchant Knowledge Base", help="title for imported knowledge base")
    parser.add_argument("--kb-source", action="append", default=[], help="KB source file or directory; can repeat")
    parser.add_argument("--kb-top-k", type=int, default=3, help="number of retrieved chunks for RAG context")
    parser.add_argument("--chunk-size", type=int, default=300, help="chunk size for KB import")
    parser.add_argument("--chunk-overlap", type=int, default=60, help="chunk overlap for KB import")
    parser.add_argument("--sentiment", default=None, help="optional sentiment hint for reply task")
    parser.add_argument("--pain-points", default="", help="optional pain points, comma-separated")
    parser.add_argument("--style-hint", default=None, help="optional style hint for reply tone")
    parser.add_argument("--results-file", default=None, help="CSV/JSON analysis results for report task")
    parser.add_argument("--output", default=None, help="optional report output path: .json/.md/.html/.svg")
    parser.add_argument("--top-k", type=int, default=5, help="top pain points for report task")
    parser.add_argument("--include-neutral", action="store_true", help="include neutral rows in pain-point aggregation")
    parser.add_argument("--estimated-orders-per-month", type=int, default=1000)
    parser.add_argument("--average-order-value", type=float, default=99.0)
    parser.add_argument("--return-loss-rate", type=float, default=0.15)
    parser.add_argument("--host", default="127.0.0.1", help="API host for serve-api task")
    parser.add_argument("--port", type=int, default=8000, help="API port for serve-api task")

    args = parser.parse_args()

    if args.task == "serve-api":
        _run_api_server(args.host, args.port)
        return

    if args.task == "kb-import":
        if not args.kb_source:
            raise SystemExit("--kb-source is required for --task kb-import")
        payload = import_knowledge_base(
            merchant_slug=args.merchant_slug,
            title=args.kb_title,
            source_paths=args.kb_source,
            chunk_size=args.chunk_size,
            overlap=args.chunk_overlap,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.task == "kb-list":
        payload = {
            "merchant_slug": args.merchant_slug,
            "indices": list_knowledge_base_indices(args.merchant_slug),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.task == "kb-search":
        kb_index_path = args.kb_index_path
        if not kb_index_path:
            if not args.kb_index_id:
                raise SystemExit("--kb-index-path or --kb-index-id is required for --task kb-search")
            from knowledge_base import resolve_knowledge_base_index_path

            kb_index_path = str(resolve_knowledge_base_index_path(args.merchant_slug, args.kb_index_id))
        if args.file and args.text is not None:
            raise SystemExit("use either positional text or --file, not both")
        query_text = _read_text_arg(args.text, args.file).strip()
        if not query_text:
            raise SystemExit("empty input text")
        payload = search_knowledge_base_index_file(kb_index_path, query_text, top_k=args.kb_top_k)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.task == "report":
        if not args.results_file:
            raise SystemExit("--results-file is required for --task report")
        records = _load_result_records(Path(args.results_file))
        payload = build_business_insight_payload(
            records,
            source_name=args.results_file,
            top_k=args.top_k,
            include_neutral=args.include_neutral,
            estimated_orders_per_month=args.estimated_orders_per_month,
            average_order_value=args.average_order_value,
            return_loss_rate=args.return_loss_rate,
            language=args.summary_language,
        )
        if args.output:
            _write_report_file(payload, Path(args.output))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

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
            kb_text = _read_text_arg(None, args.kb_file) if args.kb_file else ""
            pain_points = [x.strip() for x in (args.pain_points or "").split(",") if x.strip()]
            result = generate_customer_service_reply_as_dict(
                review_text=review_text,
                merchant_rules=rules_text,
                sentiment=args.sentiment,
                pain_points=pain_points or None,
                style_hint=args.style_hint,
                reply_language=args.reply_language,
                knowledge_base_text=kb_text,
                knowledge_base_index_path=args.kb_index_path,
                kb_top_k=args.kb_top_k,
            )

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        raise SystemExit(f"[{provider.upper()} ERROR] {type(exc).__name__}: {exc}") from exc


if __name__ == "__main__":
    main()
