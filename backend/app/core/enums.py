"""공통 Enum 정의(§18.3).

상태값은 문자열 리터럴 대신 본 Enum 을 사용한다.
"""

from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_RETRY = "WAITING_RETRY"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL_SUCCEEDED = "PARTIAL_SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    TIMEOUT = "TIMEOUT"


class AIStepStatus(str, Enum):
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    MODEL_RUNNING = "MODEL_RUNNING"
    MODEL_COMPLETED = "MODEL_COMPLETED"
    RESPONSE_RETURNED = "RESPONSE_RETURNED"


class DocType(str, Enum):
    PAPER = "paper"
    NEWS = "news"
    LAW = "law"


class ImportanceLabel(str, Enum):
    CORE = "core"
    SUPPORT = "support"
    CONTEXT = "context"
    NOISE = "noise"
