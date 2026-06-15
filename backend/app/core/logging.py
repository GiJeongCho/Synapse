"""로깅 표준(§16).

모든 로거는 ``Synapse`` 자식 로거다. ``print`` 금지 → ``logger`` 사용.
포맷: ``시간(KST) | LEVEL | name:line | message``. 레벨/컬러는 settings 로 제어(하드코딩 금지).
"""

from __future__ import annotations

import logging

from app.core.config import settings

_ROOT_NAME = "Synapse"
_CONFIGURED = False

_FMT = "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    root = logging.getLogger(_ROOT_NAME)
    root.setLevel(settings.log_level.upper())
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_FMT))
        root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def logger(name: str) -> logging.Logger:
    """모듈별 자식 로거를 반환한다.

    사용 예::

        from app.common import logger
        log = logger(__name__)
    """
    _configure_root()
    return logging.getLogger(f"{_ROOT_NAME}.{name}")


def setup_library_logging() -> None:
    """소음이 큰 외부 라이브러리 로그를 억제한다(neo4j/httpx 등)."""
    for noisy in ("neo4j", "httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
