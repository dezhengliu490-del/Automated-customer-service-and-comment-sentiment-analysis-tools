from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from edge_cases import assess_text_edge_cases, build_customer_service_handoff_reply, prepare_text_for_llm


class EdgeCaseTests(unittest.TestCase):
    def test_emoji_only_input_handoffs_to_human(self) -> None:
        assessment = assess_text_edge_cases("😡😡😡😡😡")

        self.assertIn("emoji_heavy", assessment.flags)
        self.assertEqual(assessment.guardrail_action, "handoff_human")
        self.assertTrue(assessment.should_handoff)

    def test_sarcasm_keeps_conservative_llm_path(self) -> None:
        assessment = assess_text_edge_cases("真不错啊，等了十天终于收到一个压坏的盒子。")

        self.assertIn("sarcasm_possible", assessment.flags)
        self.assertEqual(assessment.guardrail_action, "conservative")

    def test_long_input_is_truncated_for_llm(self) -> None:
        text = "包装破损，物流很慢。" * 1000
        prepared = prepare_text_for_llm(text, max_chars=800)

        self.assertLessEqual(len(prepared), 860)
        self.assertIn("input truncated", prepared)

    def test_handoff_reply_is_plain_customer_service_text(self) -> None:
        reply = build_customer_service_handoff_reply("zh")

        self.assertIn("转人工", reply)
        self.assertIn("订单号", reply)


if __name__ == "__main__":
    unittest.main()
