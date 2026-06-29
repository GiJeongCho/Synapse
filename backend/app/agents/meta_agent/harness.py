"""하네스(Harness) — LLM 노드를 견고하게 감싸는 보호막.

한 노드의 LLM 응답이 JSON으로 안 풀려도 전체 생성이 500으로 죽지 않도록,
복구 지시를 붙여 재시도하고, 끝내 실패하면 안전한 fallback 을 돌려준다.

사용:
    data = await ainvoke_json(llm, messages, node="provisioner", fallback={"tools": []})
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)

_REPAIR_INSTRUCTION = (
    "Your previous response could NOT be parsed as JSON. "
    "Return ONLY a single valid JSON value — no markdown, no code fences, no prose. "
    "Inside string values, properly escape quotes and backslashes, and keep the JSON "
    "structurally complete (all braces/brackets closed). Do not truncate."
)


async def ainvoke_json(
    llm: Any,
    messages: list[Any],
    *,
    node: str = "",
    retries: int = 2,
    fallback: Any | None = None,
) -> Any:
    """LLM 을 호출해 JSON 을 파싱한다. 실패하면 복구 지시로 재시도한다.

    - retries: 추가 재시도 횟수 (총 호출 = retries + 1)
    - fallback: 모든 시도가 실패했을 때 반환할 값. None 이면 마지막 예외를 raise.
    """
    base = list(messages)
    last_exc: Exception | None = None
    last_raw = ""

    for attempt in range(retries + 1):
        try:
            response = await llm.ainvoke(base if attempt == 0 else _with_repair(messages, last_raw))
        except Exception as exc:  # noqa: BLE001 — LLM 호출 자체 실패도 흡수
            last_exc = exc
            log.warning("하네스[%s] LLM 호출 실패 (attempt %d): %s", node, attempt, exc)
            continue

        last_raw = str(getattr(response, "content", "") or "")
        try:
            return extract_json_from_llm_response(last_raw)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            log.warning(
                "하네스[%s] JSON 파싱 실패 (attempt %d/%d): %.120s",
                node, attempt + 1, retries + 1, last_raw,
            )

    if fallback is not None:
        log.error("하네스[%s] 모든 시도 실패 — fallback 사용", node)
        return fallback
    assert last_exc is not None
    raise last_exc


def _with_repair(messages: list[Any], broken: str) -> list[Any]:
    """원본 메시지에 '깨진 출력 + 복구 지시'를 덧붙인 메시지 목록을 만든다."""
    repaired = list(messages)
    if broken:
        repaired.append(AIMessage(content=broken[:4000]))
    repaired.append(HumanMessage(content=_REPAIR_INSTRUCTION))
    return repaired
