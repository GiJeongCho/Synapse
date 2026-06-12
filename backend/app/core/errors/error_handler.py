"""재시도 데코레이터(§17.2).

``retry_on`` 으로 대상 예외를 좁힌다(무차별 재시도 금지).
``raise_error=False`` + ``fallback_value`` 로 graceful degradation 이 가능하다.
"""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, Tuple, Type

from app.core.errors.exceptions import AICoreError
from app.core.logging import logger

log = logger(__name__)


def handle_ai_error(
    *,
    retry_count: int = 0,
    retry_delay: float = 1.0,
    retry_on: Tuple[Type[Exception], ...] = (),
    raise_error: bool = True,
    fallback_value: Any = None,
) -> Callable:
    """비동기 함수를 감싸 지정 예외에 한해 재시도한다."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except retry_on as exc:  # type: ignore[misc]
                    attempt += 1
                    if attempt > retry_count:
                        if raise_error:
                            raise
                        log.warning("재시도 한도 초과, fallback 반환: %s", exc)
                        return fallback_value
                    log.warning(
                        "재시도 %d/%d (%s): %s",
                        attempt,
                        retry_count,
                        func.__name__,
                        exc,
                    )
                    await asyncio.sleep(retry_delay)
                except AICoreError:
                    raise
                except Exception:
                    raise

        return wrapper

    return decorator
