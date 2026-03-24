"""
第三周后端入口：单条文本输入 -> Gemini -> 结构化 JSON 输出。

安装依赖（在 backend 目录）:
  pip install -r requirements.txt

测试 main（会调用 Gemini API；密钥需放在 backend/.env 或环境变量 GEMINI_API_KEY 中）:

  在项目根目录（已激活 .venv 时）:
    python backend/main.py "这条评论质量不错，就是物流有点慢"

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
    """根据参数从文件、参数或标准输入读取文本。"""
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            raise SystemExit(f"文件未找到: {path}")
        return path.read_text(encoding="utf-8")
    if args.text is not None:
        return args.text
    return sys.stdin.read()


def main() -> None:
    """解析命令行参数并执行分析任务。"""
    parser = argparse.ArgumentParser(
        description="通过 Gemini API 分析单条评论；并打印结构化 JSON 结果。"
    )
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        help="单条评论文本。如果省略，则从标准输入（stdin）读取。",
    )
    parser.add_argument(
        "--file",
        "-f",
        metavar="PATH",
        help="从指定的 UTF-8 文件中读取评论文本，而不是从命令行参数或标准输入读取。",
    )
    args = parser.parse_args()

    # 检查互斥参数
    if args.file and args.text is not None:
        raise SystemExit("请使用位置参数文本或 --file 参数，不要同时使用两者。")

    body = _read_text(args).strip()
    if not body:
        raise SystemExit("无输入文本：请传入字符串、使用 --file 或管道输入。")

    try:
        # 执行分析并获取 JSON 字符串
        out = analyze_review_text_json_string(body)
    except genai_errors.ClientError as e:
        raise SystemExit(f"Gemini API 错误: {e}") from e
    except RuntimeError as e:
        raise SystemExit(str(e)) from e
    except ValueError as e:
        raise SystemExit(str(e)) from e

    # 打印最终结果
    print(out)


if __name__ == "__main__":
    main()
