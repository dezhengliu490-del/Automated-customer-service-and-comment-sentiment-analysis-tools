from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

from openai import AsyncOpenAI, OpenAI

from config import (
    get_deepseek_api_key,
    get_llm_concurrency,
    get_llm_max_retries,
    get_llm_rate_limit_rps,
    get_llm_retry_base_delay,
    get_llm_retry_max_delay,
    get_llm_timeout_seconds,
)
from edge_cases import assess_text_edge_cases, build_defensive_context, prepare_text_for_llm
from llm_base import LLMService
from observability import fingerprint_text, log_llm_call, make_request_id
from prompts import build_system_instruction, build_user_prompt, normalize_summary_language
from resilience import RetryConfig, TokenBucketRateLimiter, run_with_retry, run_with_retry_async
from schemas import SentimentAnalysisResult


class DeepSeekService(LLMService):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or get_deepseek_api_key()
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.base_url = "https://api.deepseek.com"
        self.timeout_seconds = get_llm_timeout_seconds()
        self.retry_config = RetryConfig(
            max_retries=get_llm_max_retries(),
            base_delay=get_llm_retry_base_delay(),
            max_delay=get_llm_retry_max_delay(),
        )
        self._rate_limiter = TokenBucketRateLimiter(get_llm_rate_limit_rps())
        self._semaphore = asyncio.Semaphore(get_llm_concurrency())

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self._async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    @staticmethod
    def _validate_input(review_text: str) -> str:
        text = (review_text or "").strip()
        if not text:
            raise ValueError("review text cannot be empty")
        return text

    @staticmethod
    def _json_instruction() -> str:
        return (
            "\n\nReturn strict JSON only, no markdown fences. JSON schema:\n"
            + json.dumps(SentimentAnalysisResult.model_json_schema(), ensure_ascii=False)
        )

    def _messages(
        self,
        text: str,
        summary_language: str,
        defensive_context: str = "",
    ) -> list[dict[str, str]]:
        user_prompt = build_user_prompt(text, summary_language=summary_language)
        if defensive_context:
            user_prompt = f"{user_prompt}\n\n{defensive_context}"
        return [
            {
                "role": "system",
                "content": build_system_instruction(summary_language) + self._json_instruction(),
            },
            {"role": "user", "content": user_prompt},
        ]

    def analyze_review(self, review_text: str, summary_language: str = "zh") -> SentimentAnalysisResult:
        text = self._validate_input(review_text)
        assessment = assess_text_edge_cases(text)
        prepared_text = prepare_text_for_llm(text)
        lang = normalize_summary_language(summary_language)
        messages = self._messages(prepared_text, lang, build_defensive_context(assessment, lang))
        started = time.perf_counter()
        attempts = 1
        request_id = make_request_id("analyze_review")
        input_hash = fingerprint_text(text)
        try:
            response, attempts = run_with_retry(
                lambda: self._sync_call_once(messages),
                retry_config=self.retry_config,
            )
            body = response.choices[0].message.content
            if body is None or not str(body).strip():
                raise RuntimeError("empty response from DeepSeek")
            result = SentimentAnalysisResult.model_validate_json(body)
            log_llm_call(
                provider="deepseek",
                model=self.model,
                operation="analyze_review",
                status="ok",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
                request_id=request_id,
                input_hash=input_hash,
                edge_flags=assessment.flags,
                extra={
                    "prepared_text_length": assessment.prepared_length,
                    "guardrail_action": assessment.guardrail_action,
                },
            )
            return result
        except Exception as exc:
            log_llm_call(
                provider="deepseek",
                model=self.model,
                operation="analyze_review",
                status="error",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
                request_id=request_id,
                input_hash=input_hash,
                error_type=type(exc).__name__,
                error_message=str(exc),
                edge_flags=assessment.flags,
                extra={
                    "prepared_text_length": assessment.prepared_length,
                    "guardrail_action": assessment.guardrail_action,
                },
            )
            raise

    def _sync_call_once(self, messages: list[dict[str, str]]):
        self._rate_limiter.acquire()
        return self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=self.timeout_seconds,
        )

    def analyze_review_as_dict(self, review_text: str, summary_language: str = "zh") -> dict[str, Any]:
        return self.analyze_review(review_text, summary_language=summary_language).model_dump()

    async def async_analyze_review(
        self, review_text: str, summary_language: str = "zh"
    ) -> SentimentAnalysisResult:
        text = self._validate_input(review_text)
        assessment = assess_text_edge_cases(text)
        prepared_text = prepare_text_for_llm(text)
        lang = normalize_summary_language(summary_language)
        messages = self._messages(prepared_text, lang, build_defensive_context(assessment, lang))
        started = time.perf_counter()
        attempts = 1
        request_id = make_request_id("async_analyze_review")
        input_hash = fingerprint_text(text)
        try:
            async with self._semaphore:
                response, attempts = await run_with_retry_async(
                    lambda: self._async_call_once(messages),
                    retry_config=self.retry_config,
                )
            body = response.choices[0].message.content
            if body is None or not str(body).strip():
                raise RuntimeError("empty response from DeepSeek")
            result = SentimentAnalysisResult.model_validate_json(body)
            log_llm_call(
                provider="deepseek",
                model=self.model,
                operation="async_analyze_review",
                status="ok",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
                request_id=request_id,
                input_hash=input_hash,
                edge_flags=assessment.flags,
                extra={
                    "prepared_text_length": assessment.prepared_length,
                    "guardrail_action": assessment.guardrail_action,
                },
            )
            return result
        except Exception as exc:
            log_llm_call(
                provider="deepseek",
                model=self.model,
                operation="async_analyze_review",
                status="error",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
                request_id=request_id,
                input_hash=input_hash,
                error_type=type(exc).__name__,
                error_message=str(exc),
                edge_flags=assessment.flags,
                extra={
                    "prepared_text_length": assessment.prepared_length,
                    "guardrail_action": assessment.guardrail_action,
                },
            )
            raise

    async def _async_call_once(self, messages: list[dict[str, str]]):
        await self._rate_limiter.acquire_async()
        return await self._async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=self.timeout_seconds,
        )

    async def async_analyze_review_as_dict(
        self, review_text: str, summary_language: str = "zh"
    ) -> dict[str, Any]:
        result = await self.async_analyze_review(review_text, summary_language=summary_language)
        return result.model_dump()
