"""도메인 예외 계층(§15.2, §17).

``AICoreError`` 가 루트이며, 각 도메인 예외는 클래스 변수로
``error_code`` / ``status_code`` / ``default_message`` 를 정의한다.
신규 예외는 ``<도메인>-<번호>`` 코드 체계를 따르고 §15.2 표를 갱신한다.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class AICoreError(Exception):
    """모든 도메인 예외의 루트. 기본은 AIJOB-003 / 500."""

    error_code: str = "AIJOB-003"
    status_code: int = 500
    default_message: str = "일반 실행 실패"
    retryable: bool = False

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        details: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        if retryable is not None:
            self.retryable = retryable
        super().__init__(self.message)

    def to_dict(self, stage: str = "") -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "retryable": self.retryable,
            "stage": stage,
        }


# ---- Job / 검증 ----
class ValidationError(AICoreError):
    error_code = "AIJOB-001"
    status_code = 400
    default_message = "입력값/파라미터 검증 실패"


class JobCancelledError(AICoreError):
    error_code = "AIJOB-006"
    status_code = 409
    default_message = "사용자 취소"


class JobNotFoundError(AICoreError):
    error_code = "AIJOB-007"
    status_code = 404
    default_message = "Job ID 없음"


# ---- 워크플로우 / 도구 ----
class WorkflowError(AICoreError):
    error_code = "AGENT-001"
    default_message = "워크플로우/상태 검증 실패"


class StateValidationError(WorkflowError):
    error_code = "AGENT-001"


class ToolExecutionError(AICoreError):
    error_code = "AGENT-002"
    default_message = "도구 실행 실패"


# ---- LLM ----
class LLMError(AICoreError):
    error_code = "LLM-001"
    default_message = "LLM 일반 오류"


class LLMTokenLimitError(LLMError):
    error_code = "LLM-002"
    default_message = "컨텍스트 토큰 초과"


class LLMRateLimitError(LLMError):
    error_code = "LLM-003"
    default_message = "LLM 호출 한도 초과"
    retryable = True


class LLMProviderError(LLMError):
    error_code = "LLM-004"
    default_message = "외부 LLM 제공자 장애/타임아웃"
    retryable = True


class LLMOutputParsingError(LLMError):
    error_code = "LLM-005"
    default_message = "LLM 응답 JSON 파싱 실패"


# ---- RAG ----
class RetrievalError(AICoreError):
    error_code = "RAG-001"
    default_message = "검색 일반 오류"


class VectorDBConnectionError(RetrievalError):
    error_code = "RAG-002"
    default_message = "Vector DB 연결 실패"


class GraphDBConnectionError(RetrievalError):
    error_code = "RAG-003"
    default_message = "Graph DB 연결 실패"


class DocumentParsingError(RetrievalError):
    error_code = "RAG-004"
    default_message = "문서 파싱/청킹 실패"


class IndexingError(RetrievalError):
    error_code = "RAG-005"
    default_message = "인덱싱(적재) 실패"
