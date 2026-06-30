"""Split-then-Merge Recursive Splitter — two-pass chunker optimised for
structured documents like legal texts.

Pass 1: recursively split using separator hierarchy until every piece <= target.
Pass 2: greedily merge adjacent small pieces back up to the target ceiling.
"""

from __future__ import annotations

import tiktoken
import re

from app.config import settings

_ENC = tiktoken.get_encoding("cl100k_base")

_LEGAL_SEPARATORS = [
    r"\n제\s*\d+\s*조",      # Korean article boundary
    "\n\n",
    "\n",
    ". ",
    " ",
]

_DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _token_len(text: str) -> int:
    return len(_ENC.encode(text))


def _recursive_split_pass(text: str, target: int, separators: list[str]) -> list[str]:
    """Pass 1 — split until every piece fits within *target* tokens."""
    if _token_len(text) <= target:
        return [text] if text.strip() else []

    for sep in separators:
        import re
        is_regex_sep = sep.startswith("\\") or sep.startswith(r"\n")

        if is_regex_sep:
            # 캡처 그룹으로 분리 → 구분자 보존
            # ["앞", "\n제1조", "내용1", "\n제3조", "내용2"]
            raw = re.split(f"({sep})", text)
            # 구분자와 내용을 합쳐서 ["앞", "\n제1조내용1", "\n제3조내용2"] 형태로 재조합
            parts = [raw[0]] if raw[0].strip() else []
            for i in range(1, len(raw) - 1, 2):
                combined = raw[i] + (raw[i + 1] if i + 1 < len(raw) else "")
                parts.append(combined)
        else:
            parts = text.split(sep)

        if len(parts) <= 1:
            continue

        pieces: list[str] = []
        current = ""
        for part in parts:
            # \n\n 단위 분리 시 영어 섹션 제목을 만나면 현재 청크를 끊는다
            if sep == "\n\n" and _is_english_section_title(part):
                if current:
                    pieces.append(current.strip())
                current = part
                continue
            joiner = "" if is_regex_sep else sep
            candidate = (current + joiner + part) if current else part
            if _token_len(candidate) <= target:
                current = candidate
            else:
                if current:
                    pieces.append(current.strip())
                if _token_len(part) > target:
                    idx = separators.index(sep) if sep in separators else 0
                    sub = _recursive_split_pass(part, target, separators[idx + 1:])
                    pieces.extend(sub)
                    current = ""
                else:
                    current = part
        if current and current.strip():
            pieces.append(current.strip())
        return pieces

    # character fallback
    chars_per_chunk = target * 4
    return [text[i:i + chars_per_chunk].strip() for i in range(0, len(text), chars_per_chunk) if text[i:i + chars_per_chunk].strip()]


_ARTICLE_PATTERN = re.compile(r"^제\s*\d+\s*조", re.MULTILINE)

# 영어 논문의 주요 섹션 제목 (단독 줄로 나타날 때 청크 경계로 처리)
_ENGLISH_SECTION_TITLES = {
    "abstract", "introduction", "background", "related work",
    "method", "methods", "methodology", "experiments", "experimental setup",
    "results", "discussion", "conclusion", "conclusions",
    "acknowledgement", "acknowledgements", "references", "appendix",
}


def _is_english_section_title(piece: str) -> bool:
    """청크 조각이 영어 섹션 제목 단독 줄인지 확인."""
    stripped = piece.strip().lower()
    # 짧고(50자 이하) 알려진 섹션 이름과 완전히 일치하면 경계로 처리
    return len(stripped) <= 50 and stripped in _ENGLISH_SECTION_TITLES


def _starts_with_section_title(piece: str) -> bool:
    """청크가 영어 섹션 제목으로 시작하는지 확인 (greedy merge pass용)."""
    first_line = piece.strip().split("\n")[0].strip().lower()
    return first_line in _ENGLISH_SECTION_TITLES


def _greedy_merge_pass(pieces: list[str], ceiling: int) -> list[str]:
    """Pass 2 — merge adjacent small pieces up to *ceiling* tokens.

    한국어 조문 경계(제N조)와 영어 섹션 제목은 합치지 않고 청크 경계로 유지한다.
    """
    if not pieces:
        return []

    merged: list[str] = []
    current = pieces[0]

    for piece in pieces[1:]:
        # 한국어 조문 경계
        if _ARTICLE_PATTERN.match(piece.lstrip()):
            merged.append(current.strip())
            current = piece
            continue
        # 영어 섹션 제목 경계 (piece가 섹션 제목으로 시작하면 새 청크 시작)
        if _starts_with_section_title(piece):
            merged.append(current.strip())
            current = piece
            continue
        candidate = current + "\n\n" + piece
        if _token_len(candidate) <= ceiling:
            current = candidate
        else:
            merged.append(current.strip())
            current = piece

    if current.strip():
        merged.append(current.strip())

    return merged


def split_then_merge(
    text: str,
    target_tokens: int | None = None,
    separators: list[str] | None = None,
) -> list[str]:
    """Two-pass chunker: split → merge. Default target = settings.chunk_max_tokens."""
    target = target_tokens or settings.chunk_max_tokens
    seps = separators or _DEFAULT_SEPARATORS

    pieces = _recursive_split_pass(text, target, seps)
    return _greedy_merge_pass(pieces, settings.chunk_merge_ceiling)


def split_then_merge_legal(text: str, target_tokens: int | None = None) -> list[str]:
    """Specialised variant for legal documents with Korean article boundaries."""
    return split_then_merge(text, target_tokens, _LEGAL_SEPARATORS)
