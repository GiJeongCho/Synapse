"""CrawlAgent 프롬프트(§7)."""
from langchain_core.prompts import ChatPromptTemplate

EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 HTML/웹 콘텐츠에서 의미 있는 텍스트를 추출하는 전문가입니다.\n"
        "주어진 원본 콘텐츠에서 네비게이션, 광고, 스크립트, 스타일 등 불필요한 요소를 제거하고 "
        "본문 텍스트만 깔끔하게 추출하세요.\n\n"
        "추출된 텍스트만 출력하세요. 추가 설명이나 마크다운 포맷팅 없이 순수 텍스트로 반환하세요.",
    ),
    (
        "human",
        "URL: {url}\n\n원본 콘텐츠:\n{raw_content}",
    ),
])

NORMALIZE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 텍스트 정규화 전문가입니다.\n"
        "추출된 텍스트를 다음 기준으로 정리하세요:\n"
        "- 불필요한 공백/줄바꿈 정리\n"
        "- 깨진 문자 또는 인코딩 노이즈 제거\n"
        "- 문단 구조 보존\n"
        "- 의미 없는 반복 텍스트 제거\n\n"
        "정규화된 텍스트만 출력하세요.",
    ),
    (
        "human",
        "추출된 텍스트:\n{extracted_text}",
    ),
])
