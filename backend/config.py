"""加载后端环境配置和共享设置。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 获取当前文件所在目录下的 .env 文件路径
_ENV_PATH = Path(__file__).resolve().parent / ".env"
# 加载环境变量
load_dotenv(_ENV_PATH)


def get_gemini_api_key() -> str:
    """
    从环境变量或 .env 文件中获取 Gemini API 密钥。
    优先尝试 GEMINI_API_KEY，其次尝试 GOOGLE_API_KEY。
    """
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key or not key.strip():
        raise RuntimeError(
            "缺少 API 密钥：请在环境变量中设置 GEMINI_API_KEY 或 GOOGLE_API_KEY，"
            "或者在 backend/.env 文件中配置（参考 backend/.env.example）。"
        )
    return key.strip()


def get_gemini_model() -> str:
    """
    从环境变量获取 Gemini 模型名称，默认为 'gemini-2.0-flash'。
    """
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()


def get_llm_provider() -> str:
    """
    从环境变量获取当前的 LLM 提供商。
    """
    return os.environ.get("LLM_PROVIDER", "gemini").lower().strip()
