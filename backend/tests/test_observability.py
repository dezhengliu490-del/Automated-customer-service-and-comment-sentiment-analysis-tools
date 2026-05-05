from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class ObservabilityTests(unittest.TestCase):
    def test_llm_log_includes_trace_fields(self) -> None:
        log_dir = Path.cwd() / "tmp"
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / "unit_observability_llm_calls.jsonl"
        if log_path.exists():
            log_path.unlink()

        old_log_path = os.environ.get("LLM_LOG_PATH")
        os.environ["LLM_LOG_PATH"] = str(log_path)
        try:
            import observability

            observability = importlib.reload(observability)
            request_id = observability.make_request_id("unit_test")
            observability.log_llm_call(
                provider="demo",
                model="local",
                operation="unit_test",
                status="error",
                latency_ms=12,
                attempts=1,
                text_length=7,
                request_id=request_id,
                input_hash=observability.fingerprint_text("失败样例"),
                error_type="RuntimeError",
                error_message="boom",
                edge_flags=["gibberish"],
                extra={"guardrail_action": "handoff_human"},
            )

            payload = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["request_id"], request_id)
            self.assertEqual(payload["status"], "error")
            self.assertTrue(payload["input_hash"])
            self.assertEqual(payload["edge_flags"], ["gibberish"])
            self.assertEqual(payload["guardrail_action"], "handoff_human")
        finally:
            if old_log_path is None:
                os.environ.pop("LLM_LOG_PATH", None)
            else:
                os.environ["LLM_LOG_PATH"] = old_log_path


if __name__ == "__main__":
    unittest.main()
