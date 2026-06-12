"""Post-processing: size normalisation — split oversized chunks and merge
undersized ones to improve SC (Size Compliance)."""

from __future__ import annotations

import tiktoken

from app.config import settings
from app.preprocessing.chunkers.recursive import recursive_split

_ENC = tiktoken.get_encoding("cl100k_base")


def _token_len(text: str) -> int:
    return len(_ENC.encode(text))


def normalize_chunks(chunks: list[str]) -> list[str]:
    """Apply post-processing normalisation:
    1. Split oversized chunks (> chunk_max_tokens)
    2. Merge undersized chunks (< chunk_min_tokens) with neighbours
    """
    result = _split_oversized(chunks)
    result = _merge_undersized(result)
    return result


def _split_oversized(chunks: list[str]) -> list[str]:
    """Re-split any chunk exceeding max token limit."""
    out: list[str] = []
    for chunk in chunks:
        if _token_len(chunk) > settings.chunk_max_tokens:
            sub = recursive_split(chunk, max_tokens=settings.chunk_max_tokens, overlap_tokens=0)
            out.extend(sub)
        else:
            out.append(chunk)
    return out


def _merge_undersized(chunks: list[str]) -> list[str]:
    """Merge consecutive chunks below min token threshold with their neighbour."""
    if not chunks:
        return []

    merged: list[str] = [chunks[0]]

    for chunk in chunks[1:]:
        prev = merged[-1]
        prev_len = _token_len(prev)
        curr_len = _token_len(chunk)

        if prev_len < settings.chunk_min_tokens or curr_len < settings.chunk_min_tokens:
            candidate = prev + "\n\n" + chunk
            if _token_len(candidate) <= settings.chunk_merge_ceiling:
                merged[-1] = candidate
                continue

        merged.append(chunk)

    # final pass: if last chunk is still too small, merge with previous
    if len(merged) > 1 and _token_len(merged[-1]) < settings.chunk_min_tokens:
        candidate = merged[-2] + "\n\n" + merged[-1]
        if _token_len(candidate) <= settings.chunk_merge_ceiling:
            merged[-2] = candidate
            merged.pop()

    return merged
