"""에러 도메인 패키지."""

from app.core.errors.error_handler import handle_ai_error
from app.core.errors.exceptions import (
    AICoreError,
    DocumentParsingError,
    GraphDBConnectionError,
    IndexingError,
    JobCancelledError,
    JobNotFoundError,
    LLMError,
    LLMOutputParsingError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTokenLimitError,
    RetrievalError,
    StateValidationError,
    ToolExecutionError,
    ValidationError,
    VectorDBConnectionError,
    WorkflowError,
)

__all__ = [
    "handle_ai_error",
    "AICoreError",
    "ValidationError",
    "JobCancelledError",
    "JobNotFoundError",
    "WorkflowError",
    "StateValidationError",
    "ToolExecutionError",
    "LLMError",
    "LLMTokenLimitError",
    "LLMRateLimitError",
    "LLMProviderError",
    "LLMOutputParsingError",
    "RetrievalError",
    "VectorDBConnectionError",
    "GraphDBConnectionError",
    "DocumentParsingError",
    "IndexingError",
]
