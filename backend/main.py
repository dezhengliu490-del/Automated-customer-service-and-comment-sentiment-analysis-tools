"""
Week 3 backend entry: single text in -> Gemini -> structured JSON out.

安装依赖（在 backend 目录）:
  py -3 -m pip install -r requirements.txt

测试 main（会调用 Gemini API；密钥放在 backend/.env 或环境变量 GEMINI_API_KEY）:

  在项目根目录（已激活 .venv 时可直接用 python）:
    .venv/Scripts/python.exe backend/main.py "这条评论质量不错，就是物流有点慢"

  或在 backend 目录:
    python main.py "这条评论质量不错，就是物流有点慢"

  从文件读入:
    python main.py --file sample_review.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google.genai import errors as genai_errors

from gemini_service import analyze_review_text_json_string


def _read_text(args: argparse.Namespace) -> str:
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            raise SystemExit(f"File not found: {path}")
        return path.read_text(encoding="utf-8")
    if args.text is not None:
        return args.text
    return sys.stdin.read()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze one review via Gemini API; print structured JSON."
    )
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Single review text. If omitted, read from stdin.",
    )
    parser.add_argument(
        "--file",
        "-f",
        metavar="PATH",
        help="Read review text from a UTF-8 file instead of argv/stdin.",
    )
    args = parser.parse_args()

    if args.file and args.text is not None:
        raise SystemExit("Use either positional text or --file, not both.")

    body = _read_text(args).strip()
    if not body:
        raise SystemExit("No input text: pass a string, use --file, or pipe stdin.")

    try:
        out = analyze_review_text_json_string(body)
    except genai_errors.ClientError as e:
        raise SystemExit(f"Gemini API error: {e}") from e
    except RuntimeError as e:
        raise SystemExit(str(e)) from e
    except ValueError as e:
        raise SystemExit(str(e)) from e

    print(out)


if __name__ == "__main__":
    main()
