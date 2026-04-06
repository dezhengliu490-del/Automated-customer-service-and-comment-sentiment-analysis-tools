"""(示例/占位) OpenAI 具体的 LLM 服务实现类。"""

from __future__ import annotations

import os
from typing import Any

from llm_base import LLMService
from schemas import SentimentAnalysisResult

class OpenAIService(LLMService):
    """
    使用 OpenAI API 实现的 LLM 服务。
    注：此处仅为接口演示，实际运行需安装 openai 库并配置 API Key。
    """

    def __init__(self, api_key: str | None = None, model: str | None = "gpt-4-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL")

    def analyze_review(self, review_text: str, summary_language: str = "zh") -> SentimentAnalysisResult:
        # TODO: 使用 openai 库实现逻辑
        raise NotImplementedError("OpenAIService.analyze_review 尚未完全实现。")

    def analyze_review_as_dict(self, review_text: str, summary_language: str = "zh") -> dict[str, Any]:
        raise NotImplementedError("OpenAIService.analyze_review_as_dict 尚未实现。")

    async def async_analyze_review(
        self, review_text: str, summary_language: str = "zh"
    ) -> SentimentAnalysisResult:
        # TODO: 使用 openai 异步库实现逻辑
        raise NotImplementedError("OpenAIService.async_analyze_review 尚未实现。")

    async def async_analyze_review_as_dict(
        self, review_text: str, summary_language: str = "zh"
    ) -> dict[str, Any]:
        raise NotImplementedError("OpenAIService.async_analyze_review_as_dict 尚未实现。")
