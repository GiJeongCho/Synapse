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


def _try_repair_truncated_json(text: str) -> Any | None:
    """잘린 JSON 응답을 복구 시도한다.

    LLM이 max_tokens에 도달해 응답이 잘린 경우,
    열린 괄호/따옴표를 닫아서 파싱을 시도한다.
    """
    s = text.rstrip()

    for _ in range(20):
        try:
            return json.loads(s, strict=False)
        except json.JSONDecodeError:
            pass

        if s.endswith(","):
            s = s[:-1]
            continue

        open_braces = s.count("{") - s.count("}")
        open_brackets = s.count("[") - s.count("]")
        in_string = (s.count('"') % 2) == 1

        if in_string:
            s += '"'
        elif open_brackets > 0:
            s += "]" * open_brackets
        elif open_braces > 0:
            s += "}" * open_braces
        else:
            break

    try:
        return json.loads(s, strict=False)
    except json.JSONDecodeError:
        return None


def extract_json_from_llm_response(content: str) -> Any:
    """LLM 텍스트 응답에서 JSON 본문을 추출/파싱한다.

    코드펜스(```json ... ```)나 앞뒤 잡음을 제거하고 dict/list 로 반환한다.
    잘린 응답도 복구를 시도한다.
    """
    if content is None:
        raise LLMOutputParsingError(details={"reason": "empty content"})

    text = content.strip()

    fenced = _FENCE_RE.search(text)
    candidate = fenced.group(1) if fenced else text

    # strict=False: 문자열 값 안의 실제 줄바꿈/탭 등 제어문자를 허용한다.
    # (LLM이 "code" 같은 필드에 들여쓰기/줄바꿈을 그대로 넣어 기본 파서가 거부하는 사례 방지)
    try:
        return json.loads(candidate, strict=False)
    except json.JSONDecodeError:
        pass

    matched = _OBJ_RE.search(candidate)
    if matched:
        try:
            return json.loads(matched.group(1), strict=False)
        except json.JSONDecodeError:
            repaired = _try_repair_truncated_json(matched.group(1))
            if repaired is not None:
                return repaired

    obj_start = candidate.find("{")
    if obj_start >= 0:
        repaired = _try_repair_truncated_json(candidate[obj_start:])
        if repaired is not None:
            return repaired

    raise LLMOutputParsingError(details={"raw": text[:500]})
