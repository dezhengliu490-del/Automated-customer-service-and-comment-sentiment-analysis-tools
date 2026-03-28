"""Gemini API 服务：将单条文本输入转换为结构化的 JSON 输出。"""

from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from config import get_gemini_api_key, get_gemini_model
from prompts import SYSTEM_INSTRUCTION, build_user_prompt
from schemas import SentimentAnalysisResult


def _client() -> genai.Client:
    """初始化并返回 Gemini API 客户端。"""
    return genai.Client(api_key=get_gemini_api_key())


def analyze_review_text(review_text: str) -> SentimentAnalysisResult:
    """
    调用 Gemini API 并强制执行 JSON 架构输出；返回验证后的 Pydantic 模型。
    """
    if not review_text or not review_text.strip():
        raise ValueError("评论文本不能为空")

    client = _client()
    model = get_gemini_model()
    user_prompt = build_user_prompt(review_text)

    # 配置生成内容参数，包括系统指令和输出格式
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_json_schema=SentimentAnalysisResult.model_json_schema(),
    )

    # 调用模型生成内容
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=config,
    )

    raw = response.text
    if raw is None or not str(raw).strip():
        raise RuntimeError("Gemini 返回了空文本；请检查 API 密钥、模型名称及配额。")

    # 将 JSON 字符串验证并转换为 Pydantic 对象
    return SentimentAnalysisResult.model_validate_json(raw)


def analyze_review_text_as_dict(review_text: str) -> dict[str, Any]:
    """与 analyze_review_text 相同，但返回普通字典以便于 JSON 序列化。"""
    result = analyze_review_text(review_text)
    return result.model_dump()


def analyze_review_text_json_string(review_text: str) -> str:
    """返回格式化后的 JSON 字符串，主要用于 CLI 输出。"""
    data = analyze_review_text_as_dict(review_text)
    return json.dumps(data, ensure_ascii=False, indent=2)


async def async_analyze_review_text(review_text: str) -> SentimentAnalysisResult:
    """
    [异步] 调用 Gemini API 并强制执行 JSON 架构输出；返回验证后的 Pydantic 模型。
    """
    if not review_text or not review_text.strip():
        raise ValueError("评论文本不能为空")

    # 使用 aio 客户端
    client = genai.Client(api_key=get_gemini_api_key())
    model = get_gemini_model()
    user_prompt = build_user_prompt(review_text)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_json_schema=SentimentAnalysisResult.model_json_schema(),
    )

    # 异步调用模型生成内容
    response = await client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=config,
    )

    raw = response.text
    if raw is None or not str(raw).strip():
        raise RuntimeError("Gemini [Async] 返回了空文本。")

    return SentimentAnalysisResult.model_validate_json(raw)


async def async_analyze_review_text_as_dict(review_text: str) -> dict[str, Any]:
    """[异步] 与 async_analyze_review_text 相同，但返回普通字典。"""
    result = await async_analyze_review_text(review_text)
    return result.model_dump()
