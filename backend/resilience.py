from __future__ import annotations

import asyncio
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


def _message_for_retry(exc: BaseException) -> str:
    return str(exc).lower()


def is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, FuturesTimeoutError)):
        return True
    name = exc.__class__.__name__.lower()
    if "timeout" in name or "connection" in name:
        return True
    msg = _message_for_retry(exc)
    retry_markers = (
        "rate limit",
        "too many requests",
        "429",
        "503",
        "502",
        "504",
        "temporarily unavailable",
        "connection reset",
        "read timed out",
    )
    return any(marker in msg for marker in retry_markers)


def call_with_timeout(func: Callable[[], T], timeout_seconds: float) -> T:
    if timeout_seconds <= 0:
        return func()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(func)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            raise TimeoutError(f"request timeout after {timeout_seconds:.1f}s") from exc


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int
    base_delay: float
    max_delay: float


def run_with_retry(
    func: Callable[[], T],
    *,
    retry_config: RetryConfig,
    retryable: Callable[[BaseException], bool] = is_retryable_error,
) -> tuple[T, int]:
    max_attempts = retry_config.max_retries + 1
    for attempt in range(1, max_attempts + 1):
        try:
            return func(), attempt
        except Exception as exc:
            if attempt >= max_attempts or not retryable(exc):
                raise
            backoff = min(
                retry_config.base_delay * (2 ** (attempt - 1)),
                retry_config.max_delay,
            )
            time.sleep(backoff + random.uniform(0.0, 0.2))
    raise RuntimeError("unexpected retry state")


async def run_with_retry_async(
    func: Callable[[], Awaitable[T]],
    *,
    retry_config: RetryConfig,
    retryable: Callable[[BaseException], bool] = is_retryable_error,
) -> tuple[T, int]:
    max_attempts = retry_config.max_retries + 1
    for attempt in range(1, max_attempts + 1):
        try:
            return await func(), attempt
        except Exception as exc:
            if attempt >= max_attempts or not retryable(exc):
                raise
            backoff = min(
                retry_config.base_delay * (2 ** (attempt - 1)),
                retry_config.max_delay,
            )
            await asyncio.sleep(backoff + random.uniform(0.0, 0.2))
    raise RuntimeError("unexpected retry state")


class TokenBucketRateLimiter:
    def __init__(self, refill_rate: float, capacity: float | None = None):
        self.refill_rate = max(0.1, float(refill_rate))
        self.capacity = max(1.0, float(capacity) if capacity is not None else self.refill_rate)
        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _wait_time_for_next_token(self) -> float:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.last_refill = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return 0.0
            missing = 1.0 - self.tokens
            return missing / self.refill_rate

    def acquire(self) -> None:
        while True:
            wait = self._wait_time_for_next_token()
            if wait <= 0:
                return
            time.sleep(wait)

    async def acquire_async(self) -> None:
        while True:
            wait = self._wait_time_for_next_token()
            if wait <= 0:
                return
            await asyncio.sleep(wait)
