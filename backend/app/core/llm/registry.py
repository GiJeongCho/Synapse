"""LLM 프로바이더 레지스트리(§8.2).

provider 문자열 → LangChain Chat 모델 팩토리를 매핑한다.
새 프로바이더 추가 = 본 모듈에 ``@register("<provider>")`` 팩토리 등록.
노드 코드는 프로바이더를 알 필요가 없다.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from app.core.errors.exceptions import LLMProviderError

_REGISTRY: Dict[str, Callable[..., Any]] = {}


def register(provider: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def deco(factory: Callable[..., Any]) -> Callable[..., Any]:
        _REGISTRY[provider] = factory
        return factory

    return deco


def create_chat_model(provider: str, model_name: str, api_key: str, **gen_params: Any) -> Any:
    """provider 에 맞는 LangChain Chat 모델 인스턴스를 생성한다."""
    factory = _REGISTRY.get(provider)
    if factory is None:
        raise LLMProviderError(
            message=f"지원하지 않는 LLM provider: {provider}",
            details={"available": list(_REGISTRY)},
        )
    return factory(model_name=model_name, api_key=api_key, **gen_params)


# ---------------------------------------------------------------------------
# Provider 팩토리들 (지연 임포트로 선택적 의존성 처리)
# ---------------------------------------------------------------------------
@register("anthropic")
def _anthropic(model_name: str, api_key: str, **gen_params: Any) -> Any:
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:  # pragma: no cover - 선택 의존성
        raise LLMProviderError(
            message="langchain-anthropic 미설치", details={"cause": str(exc)}
        )
    return ChatAnthropic(model=model_name, api_key=api_key, **gen_params)


@register("openai")
def _openai(model_name: str, api_key: str, **gen_params: Any) -> Any:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover
        raise LLMProviderError(message="langchain-openai 미설치", details={"cause": str(exc)})
    return ChatOpenAI(model=model_name, api_key=api_key, **gen_params)


@register("gemini")
def _gemini(model_name: str, api_key: str, **gen_params: Any) -> Any:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:  # pragma: no cover
        raise LLMProviderError(
            message="langchain-google-genai 미설치", details={"cause": str(exc)}
        )
    return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, **gen_params)
