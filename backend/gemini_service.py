"""Gemini API: single-text in, structured JSON out."""

from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from config import get_gemini_api_key, get_gemini_model
from prompts import SYSTEM_INSTRUCTION, build_user_prompt
from schemas import SentimentAnalysisResult


def _client() -> genai.Client:
    return genai.Client(api_key=get_gemini_api_key())


def analyze_review_text(review_text: str) -> SentimentAnalysisResult:
    """
    Call Gemini with JSON schema enforced; return a validated Pydantic model.
    """
    if not review_text or not review_text.strip():
        raise ValueError("review_text must be non-empty")

    client = _client()
    model = get_gemini_model()
    user_prompt = build_user_prompt(review_text)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_json_schema=SentimentAnalysisResult.model_json_schema(),
    )

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=config,
    )

    raw = response.text
    if raw is None or not str(raw).strip():
        raise RuntimeError("Gemini returned empty text; check API key, model name, and quota.")

    return SentimentAnalysisResult.model_validate_json(raw)


def analyze_review_text_as_dict(review_text: str) -> dict[str, Any]:
    """Same as analyze_review_text but returns a plain dict for JSON serialization."""
    result = analyze_review_text(review_text)
    return result.model_dump()


def analyze_review_text_json_string(review_text: str) -> str:
    """Pretty-printed JSON string for CLI output."""
    data = analyze_review_text_as_dict(review_text)
    return json.dumps(data, ensure_ascii=False, indent=2)
