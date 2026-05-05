from __future__ import annotations

"""Prompt templates for sentiment analysis and customer-service reply generation."""


def normalize_summary_language(lang: str | None) -> str:
    raw = (lang or "zh").strip().lower()
    if raw in {"zh", "cn", "chinese"}:
        return "zh"
    if raw in {"en", "eng", "english"}:
        return "en"
    return "zh"


def build_system_instruction(summary_language: str = "zh") -> str:
    lang = normalize_summary_language(summary_language)
    if lang == "en":
        return (
            "You are an e-commerce review analysis assistant. "
            "For one review, return strict structured output with: "
            "1) sentiment (positive/neutral/negative), "
            "2) confidence between 0 and 1, "
            "3) pain_points as concise ENGLISH phrases, "
            "4) summary_zh field MUST be written in English (1-2 sentences). "
            "Do not fabricate facts. If the input is ambiguous, sarcastic, emoji-only, "
            "or mostly gibberish, use a conservative neutral label with lower confidence."
        )

    return (
        "你是电商评论分析助手。对于一条评论，请结构化输出："
        "1）sentiment（positive/neutral/negative），"
        "2）0到1之间的confidence，"
        "3）pain_points（中文简短短语，无则空列表），"
        "4）summary_zh字段必须用中文写1-2句摘要。"
        "不要编造事实。遇到阴阳怪气、纯表情、乱码或语义不清输入时，"
        "采用保守判断，必要时标为neutral并降低confidence。"
    )


def build_user_prompt(review_text: str, summary_language: str = "zh") -> str:
    text = review_text.strip()
    lang = normalize_summary_language(summary_language)
    if lang == "en":
        return (
            "Analyze the following user review and return the required structured result. "
            "Important: summary_zh must be in English, and pain_points must also be in English.\n\n"
            f"{text}"
        )
    return (
        "以下是一条用户评论，请按要求输出结构化结果。"
        "注意：summary_zh和pain_points都请使用中文。\n\n"
        f"{text}"
    )


def build_customer_service_system_instruction(reply_language: str = "zh") -> str:
    lang = normalize_summary_language(reply_language)
    if lang == "en":
        return (
            "You are a professional e-commerce customer service specialist. "
            "Write empathetic and policy-compliant replies. "
            "Use merchant rules strictly when provided. "
            "For unclear, hostile, emoji-only, or nonsensical inputs, do not guess; "
            "ask for the needed details or recommend human handoff. "
            "Output plain English text only, no markdown, no labels."
        )
    return (
        "你是专业电商客服专家。请输出真诚、安抚、合规的客服回复。"
        "若提供商家规则，必须优先遵循。"
        "遇到语义不清、纯表情、乱码、辱骂或恶意诱导输入时，不要猜测事实，"
        "应要求补充必要信息或建议转人工。"
        "只输出回复正文，不要Markdown、不要标签。"
    )


def build_customer_service_user_prompt(
    review_text: str,
    merchant_rules: str,
    sentiment: str | None = None,
    pain_points: list[str] | None = None,
    style_hint: str | None = None,
    reply_language: str = "zh",
    retrieved_context: str | None = None,
    defensive_context: str | None = None,
) -> str:
    lang = normalize_summary_language(reply_language)
    s = (sentiment or "unknown").strip()

    if lang == "en":
        rules = (merchant_rules or "").strip() or "(No merchant rules provided)"
        pp = ", ".join(pain_points or []) if pain_points else "none"
        style = (style_hint or "default customer-service tone").strip()
        kb = (retrieved_context or "").strip() or "(No retrieved knowledge chunks)"
        defense = (defensive_context or "").strip() or "(No defensive edge-case note)"
        return (
            f"[Customer review]\n{review_text.strip()}\n\n"
            f"[Sentiment hint]\n{s}\n\n"
            f"[Pain points]\n{pp}\n\n"
            f"[Merchant rules]\n{rules}\n\n"
            f"[Retrieved knowledge chunks]\n{kb}\n\n"
            f"[Defensive note]\n{defense}\n\n"
            f"[Style hint]\n{style}\n\n"
            "Please generate ONE customer-service reply in English."
        )

    rules = (merchant_rules or "").strip() or "（未提供商家规则）"
    pp = "、".join(pain_points or []) if pain_points else "无"
    style = (style_hint or "默认客服语气").strip()
    kb = (retrieved_context or "").strip() or "（未检索到额外知识片段）"
    defense = (defensive_context or "").strip() or "（无特殊边界输入提示）"
    return (
        f"【用户评论】\n{review_text.strip()}\n\n"
        f"【情感倾向】\n{s}\n\n"
        f"【痛点短语】\n{pp}\n\n"
        f"【商家规则】\n{rules}\n\n"
        f"【检索知识片段】\n{kb}\n\n"
        f"【防御性处理提示】\n{defense}\n\n"
        f"【风格偏好】\n{style}\n\n"
        "请优先遵循商家规则和检索知识片段，生成一段中文客服回复。"
    )


# Backward compatibility for existing imports
REPLY_SYSTEM_INSTRUCTION = build_customer_service_system_instruction("zh")


def build_reply_user_prompt(review_text: str, sentiment: str, pain_points: list[str]) -> str:
    return build_customer_service_user_prompt(
        review_text=review_text,
        merchant_rules="",
        sentiment=sentiment,
        pain_points=pain_points,
        reply_language="zh",
    )
