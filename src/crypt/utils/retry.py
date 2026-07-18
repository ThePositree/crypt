from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from loguru import logger

_T = TypeVar("_T")


async def retry_with_backoff(
    coro_fn: Callable[[], Awaitable[_T]],
    *,
    max_attempts: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    label: str = "",
    no_retry_on: Callable[[Exception], bool] | None = None,
) -> _T:
    """
    Retry an async callable with full-jitter exponential backoff.

    Sleep formula (full jitter): uniform(0, min(max_delay, base_delay * 2**attempt))
    This avoids thundering-herd when several coroutines fail simultaneously.

    no_retry_on: optional predicate; when it returns True the exception is
    re-raised immediately without sleeping (use for permanent errors where
    retrying is guaranteed to fail, e.g. OKX 50030 "Illegal time range").

    Raises the last exception if all attempts are exhausted.
    """
    last_exc: BaseException | None = None

    for attempt in range(max_attempts):
        try:
            return await coro_fn()
        except Exception as exc:
            last_exc = exc

            if no_retry_on is not None and no_retry_on(exc):
                logger.debug(
                    "retry_with_backoff{}: non-retryable error, aborting immediately: {}",
                    f" [{label}]" if label else "",
                    exc,
                )
                raise

            if attempt == max_attempts - 1:
                logger.error(
                    "retry_with_backoff{}: all {} attempts exhausted: {}",
                    f" [{label}]" if label else "",
                    max_attempts,
                    exc,
                )
                raise

            cap = min(max_delay, base_delay * (2**attempt))
            sleep = random.uniform(0, cap) if jitter else cap
            logger.warning(
                "retry_with_backoff{}: attempt {}/{} failed ({}), retrying in {:.1f}s",
                f" [{label}]" if label else "",
                attempt + 1,
                max_attempts,
                exc,
                sleep,
            )
            await asyncio.sleep(sleep)

    # Unreachable — loop always raises or returns, but satisfies mypy.
    assert last_exc is not None
    raise last_exc
