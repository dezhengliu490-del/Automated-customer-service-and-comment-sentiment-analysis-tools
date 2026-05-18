from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from prompts import (
    build_customer_service_system_instruction,
    build_customer_service_user_prompt,
    build_defensive_prompt_principles,
    build_system_instruction,
    build_user_prompt,
)


class PromptContractTests(unittest.TestCase):
    def test_analysis_prompt_enforces_english_output_contract(self) -> None:
        system_prompt = build_system_instruction("en")
        user_prompt = build_user_prompt("The package arrived broken and support never replied.", "en")

        self.assertIn("pain_points as concise ENGLISH phrases", system_prompt)
        self.assertIn("summary_zh field MUST be written in English", system_prompt)
        self.assertIn("pain_points must also be in English", user_prompt)

    def test_analysis_prompt_enforces_chinese_output_contract(self) -> None:
        system_prompt = build_system_instruction("zh")
        user_prompt = build_user_prompt("包装破损，而且客服回复很慢。", "zh")

        self.assertIn("pain_points（中文简短短语", system_prompt)
        self.assertIn("summary_zh字段必须用中文", system_prompt)
        self.assertIn("summary_zh和pain_points都请使用中文", user_prompt)

    def test_defensive_principles_include_conservative_behavior(self) -> None:
        zh_rules = build_defensive_prompt_principles("zh")
        en_rules = build_defensive_prompt_principles("en")

        self.assertIn("保守策略", zh_rules)
        self.assertIn("respond conservatively", en_rules)
        self.assertIn("override your role", en_rules)

    def test_customer_service_prompt_contains_rules_and_rag_context(self) -> None:
        prompt = build_customer_service_user_prompt(
            review_text="包装破损，想退款。",
            merchant_rules="先致歉，再确认订单，再给退款或补发方案。",
            sentiment="negative",
            pain_points=["包装破损"],
            style_hint="专业但温和",
            reply_language="zh",
            retrieved_context="签收后 7 天内支持售后处理。",
            defensive_context="若信息不足，优先索取订单号或建议转人工。",
        )

        self.assertIn("【商家规则】", prompt)
        self.assertIn("【检索知识片段】", prompt)
        self.assertIn("【防御性处理提示】", prompt)
        self.assertIn("建议转人工", prompt)

    def test_customer_service_system_prompt_requires_plain_text(self) -> None:
        zh_prompt = build_customer_service_system_instruction("zh")
        en_prompt = build_customer_service_system_instruction("en")

        self.assertIn("只输出回复正文", zh_prompt)
        self.assertIn("Output plain English text only", en_prompt)


if __name__ == "__main__":
    unittest.main()
