"""定义 Gemini 结构化输出的 JSON 模式。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SentimentAnalysisResult(BaseModel):
    """
    MVP 单文本分析结果：包含情感、痛点及摘要（第三周流水线定义）。
    """

    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="整体评论情感：positive (好评), neutral (中评), negative (差评)。"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="模型对情感标签的置信度，范围在 0 到 1 之间。",
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description=(
            "具体的商品或服务痛点，使用简短中文短语表示"
            "（例如：物流慢、包装破损、尺寸不符）。若无则返回空列表。"
        ),
    )
    summary_zh: str = Field(
        description="用一两句中文概括评论内容，供商家参考。"
    )
