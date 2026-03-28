"""
Retry utility for external API calls.

Provides a simple decorator and helper for retrying transient failures
when calling Twilio, Resend, Telnyx, Stripe, etc.
"""

import logging
import time
from functools import wraps
from typing import TypeVar, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Exceptions that indicate transient / retryable failures
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

try:
    import httpx
    RETRYABLE_EXCEPTIONS = (*RETRYABLE_EXCEPTIONS, httpx.TransportError)
except ImportError:
    pass


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable: tuple = RETRYABLE_EXCEPTIONS,
):
    """
    Decorator that retries a function on transient failures.

    Uses exponential backoff: delay doubles each attempt (1s, 2s, 4s).
    Only retries on exceptions in `retryable`; other exceptions propagate
    immediately.

    Usage::

        @with_retry(max_attempts=3)
        def send_email(to, subject, body):
            ...
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except retryable as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            fn.__name__, max_attempts, exc,
                        )
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "%s attempt %d/%d failed (%s), retrying in %.1fs",
                        fn.__name__, attempt, max_attempts, exc, delay,
                    )
                    time.sleep(delay)
            raise last_exc  # unreachable, but satisfies type checker
        return wrapper
    return decorator
