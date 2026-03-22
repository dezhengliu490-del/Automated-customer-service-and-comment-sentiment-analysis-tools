"""Structured JSON schemas for Gemini structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SentimentAnalysisResult(BaseModel):
    """MVP single-text analysis: sentiment + pain points (Week 3 pipeline)."""

    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Overall review sentiment: positive (好评), neutral (中评), negative (差评)."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence in the sentiment label, between 0 and 1.",
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description=(
            "Concrete product or service pain points in short Chinese phrases "
            "(e.g. 物流慢, 包装破损, 尺寸不符). Empty if none."
        ),
    )
    summary_zh: str = Field(
        description="One or two sentences in Chinese summarizing the review for merchants."
    )
