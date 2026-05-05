from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from google import genai
from google.genai import types
from openai import AsyncOpenAI, OpenAI

from config import (
    get_deepseek_api_key,
    get_gemini_api_key,
    get_gemini_model,
    get_llm_concurrency,
    get_llm_max_retries,
    get_llm_provider,
    get_llm_rate_limit_rps,
    get_llm_retry_base_delay,
    get_llm_retry_max_delay,
    get_llm_timeout_seconds,
)
from edge_cases import (
    assess_text_edge_cases,
    build_customer_service_handoff_reply,
    build_defensive_context,
    prepare_text_for_llm,
)
from observability import fingerprint_text, log_llm_call, make_request_id
from prompts import (
    build_customer_service_system_instruction,
    build_customer_service_user_prompt,
    normalize_summary_language,
)
from rag_utils import SimpleRAGIndex, build_context_from_chunks
from resilience import RetryConfig, TokenBucketRateLimiter, run_with_retry, run_with_retry_async


def _validate_review_text(review_text: str) -> str:
    text = (review_text or "").strip()
    if not text:
        raise ValueError("review_text cannot be empty")
    return text


class CustomerServiceReplyEngine:
    """Week 6 backend capability: simulated customer-service reply generation."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ):
        self.provider = (provider or get_llm_provider()).strip().lower()
        self.model = model
        self.timeout_seconds = get_llm_timeout_seconds()
        self.retry_config = RetryConfig(
            max_retries=get_llm_max_retries(),
            base_delay=get_llm_retry_base_delay(),
            max_delay=get_llm_retry_max_delay(),
        )
        self._rate_limiter = TokenBucketRateLimiter(get_llm_rate_limit_rps())
        self._semaphore = asyncio.Semaphore(get_llm_concurrency())
        self.last_request_id = ""
        self.last_edge_case_flags: list[str] = []
        self.last_guardrail_action = "normal"

        if self.provider == "gemini":
            self.api_key = api_key or get_gemini_api_key()
            self.model = self.model or get_gemini_model()
            self._gemini = genai.Client(api_key=self.api_key)
            self._openai = None
            self._openai_async = None
        elif self.provider == "deepseek":
            self.api_key = api_key or get_deepseek_api_key()
            self.model = self.model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            self._openai = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            self._openai_async = AsyncOpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            self._gemini = None
        else:
            raise ValueError(f"unsupported provider for customer-service reply: {self.provider}")

    def _build_messages(
        self,
        review_text: str,
        merchant_rules: str,
        *,
        sentiment: str | None,
        pain_points: list[str] | None,
        style_hint: str | None,
        reply_language: str,
        retrieved_context: str | None,
        defensive_context: str | None = None,
    ) -> tuple[str, str]:
        lang = normalize_summary_language(reply_language)
        system_instruction = build_customer_service_system_instruction(lang)
        user_prompt = build_customer_service_user_prompt(
            review_text=review_text,
            merchant_rules=merchant_rules,
            sentiment=sentiment,
            pain_points=pain_points,
            style_hint=style_hint,
            reply_language=lang,
            retrieved_context=retrieved_context,
            defensive_context=defensive_context,
        )
        return system_instruction, user_prompt

    @staticmethod
    def _retrieve_context(
        review_text: str,
        merchant_rules: str,
        knowledge_base_text: str | None,
        kb_top_k: int,
    ) -> tuple[str, list[str]]:
        kb_source = (knowledge_base_text or "").strip() or (merchant_rules or "").strip()
        if not kb_source:
            return "", []
        index = SimpleRAGIndex.from_text(kb_source, chunk_size=300, overlap=60)
        hits = index.retrieve(review_text, top_k=max(1, kb_top_k))
        context = build_context_from_chunks(hits)
        return context, [h.text for h in hits]

    def generate_reply(
        self,
        review_text: str,
        merchant_rules: str,
        *,
        sentiment: str | None = None,
        pain_points: list[str] | None = None,
        style_hint: str | None = None,
        reply_language: str = "zh",
        knowledge_base_text: str | None = None,
        kb_top_k: int = 3,
    ) -> str:
        text = _validate_review_text(review_text)
        assessment = assess_text_edge_cases(text)
        prepared_text = prepare_text_for_llm(text)
        lang = normalize_summary_language(reply_language)
        started = time.perf_counter()
        attempts = 1
        request_id = make_request_id("customer_service_reply")
        input_hash = fingerprint_text(text)
        self.last_request_id = request_id
        self.last_edge_case_flags = assessment.flags
        self.last_guardrail_action = assessment.guardrail_action

        if assessment.should_handoff:
            reply = build_customer_service_handoff_reply(lang)
            log_llm_call(
                provider=self.provider,
                model=self.model,
                operation="customer_service_reply",
                status="guarded",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=0,
                text_length=len(text),
                request_id=request_id,
                input_hash=input_hash,
                edge_flags=assessment.flags,
                extra={
                    "guardrail_action": assessment.guardrail_action,
                    "guardrail_reason": assessment.reason,
                    "prepared_text_length": assessment.prepared_length,
                },
            )
            return reply

        context, _ = self._retrieve_context(prepared_text, merchant_rules, knowledge_base_text, kb_top_k)
        defensive_context = build_defensive_context(assessment, lang)
        system_instruction, user_prompt = self._build_messages(
            prepared_text,
            merchant_rules,
            sentiment=sentiment,
            pain_points=pain_points,
            style_hint=style_hint,
            reply_language=lang,
            retrieved_context=context,
            defensive_context=defensive_context,
        )
        try:
            if self.provider == "gemini":

                def one_call():
                    self._rate_limiter.acquire()
                    response = self._gemini.models.generate_content(
                        model=self.model,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.4,
                        ),
                    )
                    val = (response.text or "").strip()
                    if not val:
                        raise RuntimeError("empty customer-service reply from Gemini")
                    return val

                reply, attempts = run_with_retry(one_call, retry_config=self.retry_config)
            else:

                def one_call():
                    self._rate_limiter.acquire()
                    response = self._openai.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.4,
                        timeout=self.timeout_seconds,
                    )
                    val = (response.choices[0].message.content or "").strip()
                    if not val:
                        raise RuntimeError("empty customer-service reply from DeepSeek")
                    return val

                reply, attempts = run_with_retry(one_call, retry_config=self.retry_config)

            log_llm_call(
                provider=self.provider,
                model=self.model,
                operation="customer_service_reply",
                status="ok",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
                request_id=request_id,
                input_hash=input_hash,
                edge_flags=assessment.flags,
                extra={
                    "guardrail_action": assessment.guardrail_action,
                    "prepared_text_length": assessment.prepared_length,
                },
            )
            return reply
        except Exception as exc:
            log_llm_call(
                provider=self.provider,
                model=self.model,
                operation="customer_service_reply",
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
                    "guardrail_action": assessment.guardrail_action,
                    "prepared_text_length": assessment.prepared_length,
                },
            )
            raise

    async def async_generate_reply(
        self,
        review_text: str,
        merchant_rules: str,
        *,
        sentiment: str | None = None,
        pain_points: list[str] | None = None,
        style_hint: str | None = None,
        reply_language: str = "zh",
        knowledge_base_text: str | None = None,
        kb_top_k: int = 3,
    ) -> str:
        text = _validate_review_text(review_text)
        assessment = assess_text_edge_cases(text)
        prepared_text = prepare_text_for_llm(text)
        lang = normalize_summary_language(reply_language)
        started = time.perf_counter()
        attempts = 1
        request_id = make_request_id("async_customer_service_reply")
        input_hash = fingerprint_text(text)
        self.last_request_id = request_id
        self.last_edge_case_flags = assessment.flags
        self.last_guardrail_action = assessment.guardrail_action

        if assessment.should_handoff:
            reply = build_customer_service_handoff_reply(lang)
            log_llm_call(
                provider=self.provider,
                model=self.model,
                operation="async_customer_service_reply",
                status="guarded",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=0,
                text_length=len(text),
                request_id=request_id,
                input_hash=input_hash,
                edge_flags=assessment.flags,
                extra={
                    "guardrail_action": assessment.guardrail_action,
                    "guardrail_reason": assessment.reason,
                    "prepared_text_length": assessment.prepared_length,
                },
            )
            return reply

        context, _ = self._retrieve_context(prepared_text, merchant_rules, knowledge_base_text, kb_top_k)
        defensive_context = build_defensive_context(assessment, lang)
        system_instruction, user_prompt = self._build_messages(
            prepared_text,
            merchant_rules,
            sentiment=sentiment,
            pain_points=pain_points,
            style_hint=style_hint,
            reply_language=lang,
            retrieved_context=context,
            defensive_context=defensive_context,
        )
        try:
            async with self._semaphore:
                if self.provider == "gemini":

                    async def one_call():
                        await self._rate_limiter.acquire_async()
                        response = await asyncio.wait_for(
                            self._gemini.aio.models.generate_content(
                                model=self.model,
                                contents=user_prompt,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_instruction,
                                    temperature=0.4,
                                ),
                            ),
                            timeout=self.timeout_seconds,
                        )
                        val = (response.text or "").strip()
                        if not val:
                            raise RuntimeError("empty customer-service reply from Gemini")
                        return val

                else:

                    async def one_call():
                        await self._rate_limiter.acquire_async()
                        response = await self._openai_async.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.4,
                            timeout=self.timeout_seconds,
                        )
                        val = (response.choices[0].message.content or "").strip()
                        if not val:
                            raise RuntimeError("empty customer-service reply from DeepSeek")
                        return val

                reply, attempts = await run_with_retry_async(one_call, retry_config=self.retry_config)

            log_llm_call(
                provider=self.provider,
                model=self.model,
                operation="async_customer_service_reply",
                status="ok",
                latency_ms=int((time.perf_counter() - started) * 1000),
                attempts=attempts,
                text_length=len(text),
                request_id=request_id,
                input_hash=input_hash,
                edge_flags=assessment.flags,
                extra={
                    "guardrail_action": assessment.guardrail_action,
                    "prepared_text_length": assessment.prepared_length,
                },
            )
            return reply
        except Exception as exc:
            log_llm_call(
                provider=self.provider,
                model=self.model,
                operation="async_customer_service_reply",
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
                    "guardrail_action": assessment.guardrail_action,
                    "prepared_text_length": assessment.prepared_length,
                },
            )
            raise


def generate_customer_service_reply_as_dict(
    *,
    review_text: str,
    merchant_rules: str,
    provider: str | None = None,
    model: str | None = None,
    sentiment: str | None = None,
    pain_points: list[str] | None = None,
    style_hint: str | None = None,
    reply_language: str = "zh",
    knowledge_base_text: str | None = None,
    kb_top_k: int = 3,
) -> dict[str, Any]:
    engine = CustomerServiceReplyEngine(provider=provider, model=model)
    _, retrieved_chunks = engine._retrieve_context(
        review_text,
        merchant_rules,
        knowledge_base_text,
        kb_top_k,
    )
    reply = engine.generate_reply(
        review_text,
        merchant_rules,
        sentiment=sentiment,
        pain_points=pain_points,
        style_hint=style_hint,
        reply_language=reply_language,
        knowledge_base_text=knowledge_base_text,
        kb_top_k=kb_top_k,
    )
    return {
        "reply_text": reply,
        "provider": engine.provider,
        "model": engine.model,
        "reply_language": normalize_summary_language(reply_language),
        "used_rules": bool((merchant_rules or "").strip() or (knowledge_base_text or "").strip()),
        "retrieved_chunks": retrieved_chunks,
        "request_id": engine.last_request_id,
        "edge_case_flags": engine.last_edge_case_flags,
        "guardrail_action": engine.last_guardrail_action,
    }


async def async_generate_customer_service_reply_as_dict(
    *,
    review_text: str,
    merchant_rules: str,
    provider: str | None = None,
    model: str | None = None,
    sentiment: str | None = None,
    pain_points: list[str] | None = None,
    style_hint: str | None = None,
    reply_language: str = "zh",
    knowledge_base_text: str | None = None,
    kb_top_k: int = 3,
) -> dict[str, Any]:
    engine = CustomerServiceReplyEngine(provider=provider, model=model)
    _, retrieved_chunks = engine._retrieve_context(
        review_text,
        merchant_rules,
        knowledge_base_text,
        kb_top_k,
    )
    reply = await engine.async_generate_reply(
        review_text,
        merchant_rules,
        sentiment=sentiment,
        pain_points=pain_points,
        style_hint=style_hint,
        reply_language=reply_language,
        knowledge_base_text=knowledge_base_text,
        kb_top_k=kb_top_k,
    )
    return {
        "reply_text": reply,
        "provider": engine.provider,
        "model": engine.model,
        "reply_language": normalize_summary_language(reply_language),
        "used_rules": bool((merchant_rules or "").strip() or (knowledge_base_text or "").strip()),
        "retrieved_chunks": retrieved_chunks,
        "request_id": engine.last_request_id,
        "edge_case_flags": engine.last_edge_case_flags,
        "guardrail_action": engine.last_guardrail_action,
    }
