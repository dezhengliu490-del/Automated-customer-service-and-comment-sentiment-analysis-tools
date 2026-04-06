from __future__ import annotations

import asyncio
import time
from typing import Any

from google import genai
from google.genai import types

from config import (
    get_gemini_api_key,
    get_gemini_model,
    get_llm_concurrency,
    get_llm_max_retries,
    get_llm_rate_limit_rps,
    get_llm_retry_base_delay,
    get_llm_retry_max_delay,
    get_llm_timeout_seconds,
)
from llm_base import LLMService
from observability import log_llm_call
from prompts import SYSTEM_INSTRUCTION, build_user_prompt
from resilience import RetryConfig, TokenBucketRateLimiter, call_with_timeout, run_with_retry, run_with_retry_async
from schemas import SentimentAnalysisResult


class GeminiService(LLMService):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or get_gemini_api_key()
        self.model = model or get_gemini_model()
        self.timeout_seconds = get_llm_timeout_seconds()
        self.retry_config = RetryConfig(
            max_retries=get_llm_max_retries(),
            base_delay=get_llm_retry_base_delay(),
            max_delay=get_llm_retry_max_delay(),
        )
        self._rate_limiter = TokenBucketRateLimiter(get_llm_rate_limit_rps())
        self._semaphore = asyncio.Semaphore(get_llm_concurrency())

        self._client = genai.Client(api_key=self.api_key)

    @staticmethod
    def _validate_input(review_text: str) -> str:
        text = (review_text or "").strip()
        if not text:
            raise ValueError("review text cannot be empty")
        return text

    def _build_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_json_schema=SentimentAnalysisResult.model_json_schema(),
        )

    def analyze_review(self, review_text: str) -> SentimentAnalysisResult:
        text = self._validate_input(review_text)
        user_prompt = build_user_prompt(text)
        started = time.perf_counter()
        attempts = 1
        try:
            raw, attempts = run_with_retry(
                lambda: (
                    self._rate_limiter.acquire(),
                    call_with_timeout(
                        lambda: self._client.models.generate_content(
                            model=self.model,
                            contents=user_prompt,
                            config=self._build_config(),
                        ),
                        timeout_seconds=self.timeout_seconds,
                    ),
                )[1],
                retry_config=self.retry_config,
            )
            body = raw.text
            if body is None or not str(body).strip():
                raise RuntimeError("empty response from Gemini")
            result = SentimentAnalysisResult.model_validate_json(body)
            log_llm_call(
                provider="gemini",
                model=self.model,
                operation="analyze_review",
                status="ok",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
            )
            return result
        except Exception as exc:
            log_llm_call(
                provider="gemini",
                model=self.model,
                operation="analyze_review",
                status="error",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise

    def analyze_review_as_dict(self, review_text: str) -> dict[str, Any]:
        return self.analyze_review(review_text).model_dump()

    async def async_analyze_review(self, review_text: str) -> SentimentAnalysisResult:
        text = self._validate_input(review_text)
        user_prompt = build_user_prompt(text)
        started = time.perf_counter()
        attempts = 1
        try:
            async with self._semaphore:
                response, attempts = await run_with_retry_async(
                    lambda: self._async_call_once(user_prompt),
                    retry_config=self.retry_config,
                )
            body = response.text
            if body is None or not str(body).strip():
                raise RuntimeError("empty response from Gemini")
            result = SentimentAnalysisResult.model_validate_json(body)
            log_llm_call(
                provider="gemini",
                model=self.model,
                operation="async_analyze_review",
                status="ok",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
            )
            return result
        except Exception as exc:
            log_llm_call(
                provider="gemini",
                model=self.model,
                operation="async_analyze_review",
                status="error",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise

    async def _async_call_once(self, user_prompt: str):
        await self._rate_limiter.acquire_async()
        return await asyncio.wait_for(
            self._client.aio.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=self._build_config(),
            ),
            timeout=self.timeout_seconds,
        )

    async def async_analyze_review_as_dict(self, review_text: str) -> dict[str, Any]:
        result = await self.async_analyze_review(review_text)
        return result.model_dump()


def analyze_review_text(review_text: str) -> SentimentAnalysisResult:
    return GeminiService().analyze_review(review_text)


def analyze_review_text_as_dict(review_text: str) -> dict[str, Any]:
    return GeminiService().analyze_review_as_dict(review_text)


async def async_analyze_review_text(review_text: str) -> SentimentAnalysisResult:
    return await GeminiService().async_analyze_review(review_text)


async def async_analyze_review_text_as_dict(review_text: str) -> dict[str, Any]:
    return await GeminiService().async_analyze_review_as_dict(review_text)
