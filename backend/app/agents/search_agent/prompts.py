"""SearchAgent 프롬프트(§7)."""
from langchain_core.prompts import ChatPromptTemplate

ORGANIZE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 검색 결과를 주제별로 그룹화하는 전문가입니다.\n"
        "검색 결과 목록을 분석하여 관련 주제별로 그룹화하고, "
        "각 그룹에 적절한 레이블을 붙여 JSON 배열로 반환하세요.\n\n"
        "출력 형식:\n"
        '[{{"topic": "주제명", "items": [{{...결과항목...}}]}}, ...]',
    ),
    (
        "human",
        "원래 질의: {query}\n\n검색 결과:\n{results}",
    ),
])

EVALUATE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 검색 결과 품질 평가자입니다.\n"
        "질의에 대해 제공된 검색 결과가 충분히 답변을 제공하는지 평가하세요.\n\n"
        "반드시 아래 JSON 형식으로만 응답하세요:\n"
        '{{"sufficient": true/false, "reasoning": "판단 근거", '
        '"missing": ["부족한 정보 1", "부족한 정보 2"]}}',
    ),
    (
        "human",
        "질의: {query}\n\n검색 결과:\n{results}",
    ),
])
