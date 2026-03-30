"""DeepSeek 具体的 LLM 服务实现类。"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI, AsyncOpenAI

from llm_base import LLMService
from prompts import SYSTEM_INSTRUCTION, build_user_prompt
from schemas import SentimentAnalysisResult

class DeepSeekService(LLMService):
    """
    使用 DeepSeek API (OpenAI 兼容接口) 实现的 LLM 服务。
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.base_url = "https://api.deepseek.com"
        
        # 初始化同步客户端
        if self.api_key:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self._async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self._client = None
            self._async_client = None

    def _check_client(self):
        if not self._client:
            raise ValueError("DeepSeek API Key 未配置，请在前端配置或 .env 中设置。")

    def analyze_review(self, review_text: str) -> SentimentAnalysisResult:
        self._check_client()
        if not review_text or not review_text.strip():
            raise ValueError("评论文本不能为空")

        user_prompt = build_user_prompt(review_text)
        
        # 针对不原生支持 schema 的模型，在系统提示词中强化 JSON 要求
        json_instruction = (
            "\n\n请严格按以下 JSON 格式输出，不要包含任何 markdown 代码块标记：\n"
            + json.dumps(SentimentAnalysisResult.model_json_schema(), ensure_ascii=False)
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION + json_instruction},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw = response.choices[0].message.content
        if raw is None or not str(raw).strip():
            raise RuntimeError("DeepSeek 返回了空文本。")

        return SentimentAnalysisResult.model_validate_json(raw)

    def analyze_review_as_dict(self, review_text: str) -> dict[str, Any]:
        return self.analyze_review(review_text).model_dump()

    async def async_analyze_review(self, review_text: str) -> SentimentAnalysisResult:
        self._check_client()
        if not review_text or not review_text.strip():
            raise ValueError("评论文本不能为空")

        user_prompt = build_user_prompt(review_text)
        json_instruction = (
            "\n\n请严格按以下 JSON 格式输出，不要包含任何 markdown 代码块标记：\n"
            + json.dumps(SentimentAnalysisResult.model_json_schema(), ensure_ascii=False)
        )

        response = await self._async_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION + json_instruction},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw = response.choices[0].message.content
        if raw is None or not str(raw).strip():
            raise RuntimeError("DeepSeek [Async] 返回了空文本。")

        return SentimentAnalysisResult.model_validate_json(raw)

    async def async_analyze_review_as_dict(self, review_text: str) -> dict[str, Any]:
        result = await self.async_analyze_review(review_text)
        return result.model_dump()
