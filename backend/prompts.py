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
    summary_req = (
        "用一两句中文概括评论内容，填入 summary_zh 字段。"
        if lang == "zh"
        else "Write a 1-2 sentence English summary in the summary_zh field."
    )
    return (
        "你是电商评论分析助手。根据用户给出的一条商品评论，完成："
        "1) 情感分类（positive / neutral / negative）；"
        "2) 给出 0~1 的 confidence；"
        "3) 提取具体 pain_points（无则空列表）；"
        f"4) {summary_req} "
        "要求：仅依据输入文本，不要编造事实；输出要结构化、简洁。"
    )


SYSTEM_INSTRUCTION = build_system_instruction("zh")


def build_user_prompt(review_text: str) -> str:
    text = review_text.strip()
    return f"以下是一条用户评论，请按要求输出结构化结果：\n\n{text}"


REPLY_SYSTEM_INSTRUCTION = """你是电商客服专家，负责为用户的商品评论撰写初步的安抚或感谢回复。
请根据评论内容、情感倾向和痛点短语，生成专业、真诚、得体的回复（约 50-100 字）。
输出要求：只输出回复正文，不要包含标签或解释。"""


def build_reply_user_prompt(review_text: str, sentiment: str, pain_points: list[str]) -> str:
    pain_points_str = "、".join(pain_points) if pain_points else "无明显具体痛点"
    return (
        f"【评论内容】：{review_text.strip()}\n"
        f"【情感倾向】：{sentiment}\n"
        f"【痛点短语】：{pain_points_str}\n\n"
        "请根据以上信息生成一段安抚/感谢回复。"
    )
