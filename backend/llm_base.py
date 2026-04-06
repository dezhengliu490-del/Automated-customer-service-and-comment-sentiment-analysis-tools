from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from schemas import SentimentAnalysisResult

class LLMService(ABC):
    """
    LLM 服务的抽象基类，用于统一不同模型供应商（Gemini, OpenAI, etc.）的接口。
    """

    @abstractmethod
    def analyze_review(self, review_text: str, summary_language: str = "zh") -> SentimentAnalysisResult:
        """
        同步文本分析。
        """
        pass

    @abstractmethod
    def analyze_review_as_dict(self, review_text: str, summary_language: str = "zh") -> dict[str, Any]:
        """
        同步文本分析，返回字典格式。
        """
        pass

    @abstractmethod
    async def async_analyze_review(
        self, review_text: str, summary_language: str = "zh"
    ) -> SentimentAnalysisResult:
        """
        异步文本分析。
        """
        pass

    @abstractmethod
    async def async_analyze_review_as_dict(
        self, review_text: str, summary_language: str = "zh"
    ) -> dict[str, Any]:
        """
        异步文本分析，返回字典格式。
        """
        pass
