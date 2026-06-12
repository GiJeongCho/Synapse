"""Split-then-Merge Recursive Splitter — two-pass chunker optimised for
structured documents like legal texts.

Pass 1: recursively split using separator hierarchy until every piece <= target.
Pass 2: greedily merge adjacent small pieces back up to the target ceiling.
"""

from __future__ import annotations

import tiktoken

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
        parts = re.split(sep, text) if sep.startswith("\\") or sep.startswith(r"\n") else text.split(sep)

        if len(parts) <= 1:
            continue

        pieces: list[str] = []
        current = ""
        for part in parts:
            candidate = (current + sep + part) if current else part
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


def _greedy_merge_pass(pieces: list[str], ceiling: int) -> list[str]:
    """Pass 2 — merge adjacent small pieces up to *ceiling* tokens."""
    if not pieces:
        return []

    merged: list[str] = []
    current = pieces[0]

    for piece in pieces[1:]:
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
