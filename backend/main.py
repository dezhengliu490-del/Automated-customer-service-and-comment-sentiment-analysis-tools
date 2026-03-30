"""
后端入口：单条文本输入 -> LLM Factory -> 结构化 JSON 输出。

支持多种大模型提供商，通过修改 .env 中的 LLM_PROVIDER 切换。
现在模型调用已抽象化为 LLMService 接口。
"""

from __future__ import annotations

import argparse
import sys
import json
from pathlib import Path

from llm_factory import get_llm_service
from config import get_llm_provider

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
    provider = get_llm_provider()
    parser = argparse.ArgumentParser(
        description=f"通过 {provider.upper()} API 分析单条评论；并打印结构化 JSON 结果。"
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
        # 1. 获取 LLM 服务实例
        service = get_llm_service()
        
        # 2. 执行分析并获取字典结果
        result_dict = service.analyze_review_as_dict(body)
        
        # 3. 转换为格式化的 JSON 字符串
        out = json.dumps(result_dict, ensure_ascii=False, indent=2)
        
    except Exception as e:
        # 通用错误处理，根据需要可以细化
        error_type = type(e).__name__
        raise SystemExit(f"[{provider.upper()} 错误] {error_type}: {e}") from e

    # 打印最终结果
    print(out)


if __name__ == "__main__":
    main()
