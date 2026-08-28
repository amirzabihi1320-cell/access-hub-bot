"""
Retry System با Exponential Backoff (بند ۲۸ سند).

عمداً Provider-agnostic نوشته شده (نه فقط Marzban) تا هر Providerی که در
آینده اضافه شود (Sanaei، یک Payment Gateway و ...) بتواند از همین تابع
استفاده کند. فقط خطاهایی که خودشان را ``retryable=True`` معرفی کرده‌اند
(یعنی مشکل موقت/شبکه‌ای است، نه رد صریح توسط Provider) دوباره امتحان
می‌شوند - خطای Validation/Auth بی‌فایده است که سه‌بار تکرار شود.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from app.providers.exceptions import ProviderError

T = TypeVar("T")

logger = logging.getLogger("access_hub.retry")


async def retry_provider_call(
    func: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    context: str = "",
) -> T:
    """
    ``func`` را تا ``max_attempts`` بار صدا می‌زند. بین تلاش‌ها به‌صورت
    نمایی صبر می‌کند (1s, 2s, 4s, ...). اگر خطا ``retryable=False`` باشد
    (مثلاً ProviderAuthError/ProviderValidationError)، بلافاصله - بدون
    اتلاف وقت روی Retry بی‌فایده - raise می‌شود.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return await func()
        except ProviderError as exc:
            if not exc.retryable or attempt >= max_attempts:
                if attempt > 1:
                    logger.warning(
                        "%s: giving up after %s attempt(s): %s", context or "provider call", attempt, exc.message
                    )
                raise
            delay = base_delay_seconds * (2 ** (attempt - 1))
            logger.info(
                "%s: attempt %s/%s failed (%s), retrying in %.1fs",
                context or "provider call", attempt, max_attempts, exc.message, delay,
            )
            await asyncio.sleep(delay)
