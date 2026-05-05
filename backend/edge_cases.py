from __future__ import annotations

"""Utilities for defensive handling of extreme or ambiguous review inputs."""

import re
import unicodedata
from dataclasses import dataclass, field

from config import get_llm_max_input_chars

_CJK_OR_WORD = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")
_REPEATED_CHARS = re.compile(r"(.)\1{8,}")
_URL_OR_SCRIPT = re.compile(r"(https?://|<script|</|javascript:)", re.IGNORECASE)
_SARCASM_HINTS = (
    "真不错啊",
    "真行",
    "谢谢你啊",
    "可真",
    "绝了",
    "呵呵",
    "也是醉了",
    "great job",
    "nice job",
    "thanks for nothing",
    "yeah right",
)
_HOSTILE_HINTS = (
    "去死",
    "傻",
    "垃圾商家",
    "骗子",
    "威胁",
    "kill yourself",
    "idiot",
    "scam",
    "fraud",
)


@dataclass(frozen=True)
class EdgeCaseAssessment:
    original_length: int
    prepared_length: int
    flags: list[str] = field(default_factory=list)
    guardrail_action: str = "normal"
    reason: str = ""

    @property
    def should_handoff(self) -> bool:
        return self.guardrail_action == "handoff_human"


def _visible_text_ratio(text: str) -> float:
    if not text:
        return 0.0
    visible = sum(1 for ch in text if not ch.isspace())
    meaningful = len(_CJK_OR_WORD.findall(text))
    return meaningful / max(visible, 1)


def _emoji_like_ratio(text: str) -> float:
    if not text:
        return 0.0
    visible = [ch for ch in text if not ch.isspace()]
    if not visible:
        return 0.0
    emoji_like = 0
    for ch in visible:
        category = unicodedata.category(ch)
        if category in {"So", "Sk"} and not _CJK_OR_WORD.match(ch):
            emoji_like += 1
    return emoji_like / len(visible)


def assess_text_edge_cases(text: str) -> EdgeCaseAssessment:
    src = (text or "").strip()
    flags: list[str] = []
    reason_parts: list[str] = []
    max_chars = get_llm_max_input_chars()

    if not src:
        return EdgeCaseAssessment(
            original_length=0,
            prepared_length=0,
            flags=["empty"],
            guardrail_action="handoff_human",
            reason="empty input",
        )

    lower = src.lower()
    meaningful_ratio = _visible_text_ratio(src)
    emoji_ratio = _emoji_like_ratio(src)

    if len(src) > max_chars:
        flags.append("very_long")
        reason_parts.append(f"input length exceeds {max_chars} characters")
    if emoji_ratio >= 0.6 and len(src) <= 80:
        flags.append("emoji_heavy")
        reason_parts.append("emoji-heavy short input")
    if meaningful_ratio < 0.25 and len(src) >= 12:
        flags.append("gibberish")
        reason_parts.append("low meaningful-character ratio")
    if _REPEATED_CHARS.search(src):
        flags.append("repeated_noise")
        reason_parts.append("contains repeated-character noise")
        if meaningful_ratio < 0.8 and "gibberish" not in flags:
            flags.append("gibberish")
            reason_parts.append("repeated noise mixed with symbols")
    if any(hint in lower or hint in src for hint in _SARCASM_HINTS):
        flags.append("sarcasm_possible")
        reason_parts.append("contains sarcasm cues")
    if any(hint in lower or hint in src for hint in _HOSTILE_HINTS):
        flags.append("hostile_language")
        reason_parts.append("contains hostile or abusive language")
    if _URL_OR_SCRIPT.search(src):
        flags.append("prompt_injection_or_link")
        reason_parts.append("contains URL/script-like content")

    handoff_flags = {"emoji_heavy", "gibberish", "hostile_language", "prompt_injection_or_link"}
    if any(flag in handoff_flags for flag in flags):
        action = "handoff_human"
    elif flags:
        action = "conservative"
    else:
        action = "normal"

    prepared = prepare_text_for_llm(src, max_chars=max_chars)
    return EdgeCaseAssessment(
        original_length=len(src),
        prepared_length=len(prepared),
        flags=flags,
        guardrail_action=action,
        reason="; ".join(reason_parts),
    )


def prepare_text_for_llm(text: str, *, max_chars: int | None = None) -> str:
    src = (text or "").strip()
    limit = max_chars or get_llm_max_input_chars()
    if limit <= 0 or len(src) <= limit:
        return src

    head_len = max(1, int(limit * 0.65))
    tail_len = max(1, limit - head_len - 80)
    return (
        src[:head_len].rstrip()
        + "\n\n[...input truncated for safety and cost control...]\n\n"
        + src[-tail_len:].lstrip()
    )


def build_defensive_context(assessment: EdgeCaseAssessment, language: str = "zh") -> str:
    if not assessment.flags:
        return ""
    flags = ", ".join(assessment.flags)
    if language == "en":
        return (
            "Defensive handling note: this input may be ambiguous or adversarial "
            f"({flags}). Stay conservative, do not invent facts, and recommend human "
            "handoff when the customer's intent is unclear."
        )
    return (
        "防御性处理提示：该输入可能存在语义模糊或对抗性特征"
        f"（{flags}）。请保持保守，不编造事实；若用户意图不清，应建议转人工处理。"
    )


def build_customer_service_handoff_reply(language: str = "zh") -> str:
    if language == "en":
        return (
            "Thanks for reaching out. The current message does not provide enough clear "
            "order or issue details for us to handle it safely. Please share the order "
            "number and the specific problem, or contact a human support agent for help."
        )
    return (
        "您好，感谢您的反馈。当前信息还不足以安全判断具体问题，"
        "建议您补充订单号、商品问题描述或相关图片；如情况紧急，也可以直接转人工客服处理。"
    )
