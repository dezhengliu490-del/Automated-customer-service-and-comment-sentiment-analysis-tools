from __future__ import annotations

"""Prompt templates for sentiment analysis and reply generation."""


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
            "3) pain_points as concise phrases, "
            "4) summary_zh field MUST be written in English (1-2 sentences). "
            "Do not fabricate facts."
        )

    return (
        "你是电商评论分析助手。对于一条评论，请结构化输出："
        "1）sentiment（positive/neutral/negative），"
        "2）0到1之间的confidence，"
        "3）pain_points（简短短语，无则空列表），"
        "4）summary_zh字段必须用中文写1-2句摘要。"
        "不要编造事实。"
    )


SYSTEM_INSTRUCTION = build_system_instruction("zh")


def build_user_prompt(review_text: str, summary_language: str = "zh") -> str:
    text = review_text.strip()
    lang = normalize_summary_language(summary_language)
    if lang == "en":
        return (
            "Analyze the following user review and return the required structured result. "
            "Important: summary_zh must be in English.\n\n"
            f"{text}"
        )
    return f"以下是一条用户评论，请按要求输出结构化结果：\n\n{text}"


REPLY_SYSTEM_INSTRUCTION = (
    "你是电商客服专家，负责为用户评论生成安抚或感谢回复。"
    "输出要求：只输出回复正文，不要包含标签或解释。"
)


def build_reply_user_prompt(review_text: str, sentiment: str, pain_points: list[str]) -> str:
    pain_points_str = "、".join(pain_points) if pain_points else "无明显具体痛点"
    return (
        f"【评论内容】：{review_text.strip()}\n"
        f"【情感倾向】：{sentiment}\n"
        f"【痛点短语】：{pain_points_str}\n\n"
        "请根据以上信息生成一段安抚/感谢回复。"
    )
