"""LLM Regex Splitter — asks an LLM to produce a single regex pattern
tailored to the document, then applies it deterministically.

Best for papers and documents with clear structural patterns (section headings,
numbered articles, etc.)."""

from __future__ import annotations

import json
import re

import tiktoken
from anthropic import Anthropic

from app.config import settings

_ENC = tiktoken.get_encoding("cl100k_base")
_SAMPLE_TOKENS = 8000


def _token_len(text: str) -> int:
    return len(_ENC.encode(text))


def _get_sample(text: str) -> str:
    """Return up to _SAMPLE_TOKENS of the document's beginning."""
    tokens = _ENC.encode(text)[:_SAMPLE_TOKENS]
    return _ENC.decode(tokens)


async def generate_regex_pattern(text: str) -> str:
    """Ask Claude to produce a single Python regex that splits this document
    at its natural structural boundaries."""
    client = Anthropic(api_key=settings.anthropic_api_key)
    sample = _get_sample(text)

    message = client.messages.create(
        model=settings.llm_model,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are an expert at analysing document structure.\n"
                    "Given the document sample below, produce ONE Python regex pattern "
                    "that can be used with `re.split(pattern, text)` to divide the full "
                    "document into semantically coherent sections.\n\n"
                    "Rules:\n"
                    "- The pattern should match section boundaries (headings, article numbers, etc.)\n"
                    "- Return ONLY valid JSON: {\"pattern\": \"<regex>\"}\n"
                    "- Use raw string escaping suitable for Python re module\n\n"
                    f"--- DOCUMENT SAMPLE ---\n{sample}"
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```\w*\n?", "", raw).strip()

    try:
        result = json.loads(raw)
        pattern = result["pattern"]
        re.compile(pattern)
        return pattern
    except (json.JSONDecodeError, KeyError, re.error):
        return r"\n#{1,3}\s+"


def _split_with_pattern(text: str, pattern: str) -> list[str]:
    # 캡처 그룹 → 비캡처 그룹으로 변환 (구분자가 청크에 포함되는 버그 방지)
    non_capturing = re.sub(r"\((?!\?)", "(?:", pattern)
    parts = re.split(non_capturing, text)
    return [p.strip() for p in parts if p and p.strip()]


async def llm_regex_split(text: str, pattern: str | None = None) -> list[str]:
    """Full pipeline: generate pattern (or use provided) → split."""
    if pattern is None:
        pattern = await generate_regex_pattern(text)

    chunks = _split_with_pattern(text, pattern)

    if not chunks:
        return [text.strip()] if text.strip() else []

    return chunks
