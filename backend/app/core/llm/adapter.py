"""LLM 어댑터 진입점(§8).

노드는 LLM 구현체를 알 필요 없이 ``get_llm_for_agent(agent_name)`` 만 호출한다.
모델/프로바이더 교체 = ``config.py`` 의 ``<AGENT>_AGENT`` 프로퍼티만 수정(노드 코드 불변).
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.errors.exceptions import LLMError
from app.core.llm.registry import create_chat_model
from app.core.logging import logger

log = logger(__name__)


def get_llm_for_agent(agent_name: str) -> Any:
    """agent_name(소문자) ↔ ``settings.<대문자>_AGENT`` 매핑으로 LLM 을 만든다(§3.2).

    예) ``get_llm_for_agent("supervisor")`` → ``settings.SUPERVISOR_AGENT``.
    반환값은 ``await llm.ainvoke(messages)`` 로 호출 가능한 LangChain Chat 모델이다.
    """
    prop = f"{agent_name.upper()}_AGENT"
    cfg = getattr(settings, prop, None)
    if cfg is None:
        raise LLMError(
            message=f"에이전트 LLM 설정 없음: {prop}",
            details={"agent_name": agent_name},
        )

    gen_params = cfg.get("gen_params", {})
    return create_chat_model(
        provider=cfg["provider"],
        model_name=cfg["model_name"],
        api_key=cfg.get("api_key", ""),
        **gen_params,
    )
