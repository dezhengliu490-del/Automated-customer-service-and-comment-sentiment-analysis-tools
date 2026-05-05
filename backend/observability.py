from __future__ import annotations

import json
import logging
import hashlib
import uuid
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


def make_request_id(operation: str = "api") -> str:
    clean = "".join(ch for ch in operation.lower() if ch.isalnum() or ch in {"_", "-"}).strip("_-")
    prefix = clean[:18] or "api"
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def fingerprint_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()[:16]


def log_backend_event(
    *,
    operation: str,
    status: str,
    request_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: int | None = None,
    attempts: int | None = None,
    text_length: int | None = None,
    input_hash: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
    edge_flags: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id or make_request_id(operation),
        "operation": operation,
        "status": status,
    }
    if provider:
        payload["provider"] = provider
    if model:
        payload["model"] = model
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    if attempts is not None:
        payload["attempts"] = attempts
    if text_length is not None:
        payload["text_length"] = text_length
    if input_hash:
        payload["input_hash"] = input_hash
    if error_type:
        payload["error_type"] = error_type
    if error_message:
        payload["error_message"] = error_message[:500]
    if edge_flags:
        payload["edge_flags"] = edge_flags
    if extra:
        payload.update(extra)

    _ensure_logger().info(json.dumps(payload, ensure_ascii=False))


def log_llm_call(
    *,
    provider: str,
    model: str,
    operation: str,
    status: str,
    latency_ms: int,
    attempts: int,
    text_length: int,
    request_id: str | None = None,
    input_hash: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
    edge_flags: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    log_backend_event(
        provider=provider,
        model=model,
        operation=operation,
        status=status,
        latency_ms=latency_ms,
        attempts=attempts,
        text_length=text_length,
        request_id=request_id,
        input_hash=input_hash,
        error_type=error_type,
        error_message=error_message,
        edge_flags=edge_flags,
        extra=extra,
    )
