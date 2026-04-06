from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from config import get_llm_log_path
except ModuleNotFoundError:  # pragma: no cover
    from .config import get_llm_log_path

_LOGGER_NAME = "backend.llm"


def _ensure_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    log_path = get_llm_log_path()
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_llm_call(
    *,
    provider: str,
    model: str,
    operation: str,
    status: str,
    latency_ms: int,
    attempts: int,
    text_length: int,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "operation": operation,
        "status": status,
        "latency_ms": latency_ms,
        "attempts": attempts,
        "text_length": text_length,
    }
    if error_type:
        payload["error_type"] = error_type
    if error_message:
        payload["error_message"] = error_message[:300]

    _ensure_logger().info(json.dumps(payload, ensure_ascii=False))
