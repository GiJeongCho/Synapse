"""LLM 응답 파싱 유틸(§8.1).

LLM 의 JSON 응답은 항상 ``extract_json_from_llm_response()`` 로 파싱한다.
실패 시 ``LLMOutputParsingError`` 를 raise 한다(§8.3).
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.errors.exceptions import LLMOutputParsingError

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_OBJ_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def extract_json_from_llm_response(content: str) -> Any:
    """LLM 텍스트 응답에서 JSON 본문을 추출/파싱한다.

    코드펜스(```json ... ```)나 앞뒤 잡음을 제거하고 dict/list 로 반환한다.
    """
    if content is None:
        raise LLMOutputParsingError(details={"reason": "empty content"})

    text = content.strip()

    fenced = _FENCE_RE.search(text)
    candidate = fenced.group(1) if fenced else text

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    matched = _OBJ_RE.search(candidate)
    if matched:
        try:
            return json.loads(matched.group(1))
        except json.JSONDecodeError as exc:
            raise LLMOutputParsingError(details={"cause": str(exc), "raw": text[:500]})

    raise LLMOutputParsingError(details={"raw": text[:500]})
