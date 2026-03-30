"""Gemini 具体的 LLM 服务实现类。"""

from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from config import get_gemini_api_key, get_gemini_model
from llm_base import LLMService
from prompts import SYSTEM_INSTRUCTION, build_user_prompt
from schemas import SentimentAnalysisResult

class GeminiService(LLMService):
    """
    使用 Google Gemini API 实现的 LLM 服务。
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or get_gemini_api_key()
        self.model = model or get_gemini_model()
        # 初始化同步客户端
        self._client = genai.Client(api_key=self.api_key)

    def analyze_review(self, review_text: str) -> SentimentAnalysisResult:
        """
        调用 Gemini API 并强制执行 JSON 架构输出；返回验证后的 Pydantic 模型。
        """
        if not review_text or not review_text.strip():
            raise ValueError("评论文本不能为空")

        user_prompt = build_user_prompt(review_text)

        # 配置生成内容参数，包括系统指令和输出格式
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_json_schema=SentimentAnalysisResult.model_json_schema(),
        )

        # 调用模型生成内容
        response = self._client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )

        raw = response.text
        if raw is None or not str(raw).strip():
            raise RuntimeError("Gemini 返回了空文本。")

        return SentimentAnalysisResult.model_validate_json(raw)

    def analyze_review_as_dict(self, review_text: str) -> dict[str, Any]:
        """返回普通字典。"""
        result = self.analyze_review(review_text)
        return result.model_dump()

    async def async_analyze_review(self, review_text: str) -> SentimentAnalysisResult:
        """
        [异步] 调用 Gemini API 并强制执行 JSON 架构输出。
        """
        if not review_text or not review_text.strip():
            raise ValueError("评论文本不能为空")

        user_prompt = build_user_prompt(review_text)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_json_schema=SentimentAnalysisResult.model_json_schema(),
        )

        # 异步调用模型生成内容 (注意：Client.aio 属性提供异步接口)
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )

        raw = response.text
        if raw is None or not str(raw).strip():
            raise RuntimeError("Gemini [Async] 返回了空文本。")

        return SentimentAnalysisResult.model_validate_json(raw)

    async def async_analyze_review_as_dict(self, review_text: str) -> dict[str, Any]:
        """[异步] 返回普通字典。"""
        result = await self.async_analyze_review(review_text)
        return result.model_dump()


# --- 为了保持向后兼容性，保留函数式接口（可选，建议逐步迁移） ---

def analyze_review_text(review_text: str) -> SentimentAnalysisResult:
    return GeminiService().analyze_review(review_text)

def analyze_review_text_as_dict(review_text: str) -> dict[str, Any]:
    return GeminiService().analyze_review_as_dict(review_text)

async def async_analyze_review_text(review_text: str) -> SentimentAnalysisResult:
    return await GeminiService().async_analyze_review(review_text)

async def async_analyze_review_text_as_dict(review_text: str) -> dict[str, Any]:
    return await GeminiService().async_analyze_review_as_dict(review_text)
