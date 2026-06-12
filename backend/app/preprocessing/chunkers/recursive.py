"""Recursive character text splitter — baseline chunker for news/general docs."""

from __future__ import annotations

import tiktoken

from app.config import settings

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
_ENC = tiktoken.get_encoding("cl100k_base")


def _token_len(text: str) -> int:
    return len(_ENC.encode(text))


def recursive_split(
    text: str,
    max_tokens: int | None = None,
    overlap_tokens: int = 50,
    separators: list[str] | None = None,
) -> list[str]:
    """Split text recursively using separator hierarchy until each piece
    fits within *max_tokens*.  Adjacent chunks share *overlap_tokens* of
    trailing context."""
    max_tokens = max_tokens or settings.chunk_max_tokens
    separators = separators or _SEPARATORS

    if _token_len(text) <= max_tokens:
        return [text.strip()] if text.strip() else []

    for sep in separators:
        if not sep:
            # character-level fallback
            parts = [text[i : i + max_tokens * 4] for i in range(0, len(text), max_tokens * 4)]
        else:
            parts = text.split(sep)

        if len(parts) <= 1:
            continue

        chunks: list[str] = []
        current = ""

        for part in parts:
            candidate = (current + sep + part) if current else part
            if _token_len(candidate) <= max_tokens:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                if _token_len(part) > max_tokens:
                    sub = recursive_split(part, max_tokens, overlap_tokens, separators[separators.index(sep) + 1 :])
                    chunks.extend(sub)
                    current = ""
                else:
                    current = part

        if current and current.strip():
            chunks.append(current.strip())

        if overlap_tokens > 0 and len(chunks) > 1:
            chunks = _add_overlap(chunks, overlap_tokens, sep)

        return [c for c in chunks if c.strip()]

    return [text.strip()] if text.strip() else []


def _add_overlap(chunks: list[str], overlap_tokens: int, sep: str) -> list[str]:
    """Add trailing overlap from previous chunk to the start of next chunk."""
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tokens = _ENC.encode(chunks[i - 1])
        overlap_text = _ENC.decode(prev_tokens[-overlap_tokens:]) if len(prev_tokens) > overlap_tokens else ""
        merged = (overlap_text + sep + chunks[i]).strip() if overlap_text else chunks[i]
        result.append(merged)
    return result
