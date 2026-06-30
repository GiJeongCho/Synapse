import os
import httpx
import json

def synthesize_paper(content="", articles=None, **kwargs):
    """Generate Korean academic paper from AI trends content."""
    # Handle both content string and articles list
    text = content or ""
    if not text and articles:
        text = "\n".join(
            f"{a.get('title', '')} - {a.get('summary', '')}"
            for a in articles if isinstance(a, dict)
        )
    
    if not text or len(text.strip()) < 50:
        return {
            "status": "error",
            "document": "",
            "message": "Insufficient content for paper generation"
        }
    
    # Get Anthropic API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "document": "",
            "message": "ANTHROPIC_API_KEY not set"
        }
    
    # Prepare prompt for academic paper generation
    instruction = """다음은 최신 AI 동향에 관한 뉴스 헤드라인과 설명 목록입니다. 본문 전문은 제공되지 않습니다.

주어진 제목과 설명만으로 한국어 학술 논문 형식의 종합 보고서를 작성하세요. 추가 내용을 요청하거나 본문이 없다고 거부하지 말고, 주어진 정보로 바로 작성하세요.

논문 구조:
1. 제목: "인공지능 최신 동향 분석"
2. 초록 (Abstract): 200-300자로 전체 내용 요약
3. 서론 (Introduction): AI 동향 연구의 중요성과 배경
4. 본론 (Main Body): 주요 트렌드를 3-4개 섹션으로 분류하여 분석 (예: 생성형 AI, 멀티모달 모델, AI 윤리, 산업 응용)
5. 결론 (Conclusion): 주요 발견사항과 향후 전망
6. 참고문헌 (References): 제공된 출처를 [1], [2] 형식으로 인용

요구사항:
- 학술적 문체 사용
- 각 주장에 대해 제공된 출처 인용
- 객관적이고 분석적인 톤 유지
- 최소 1500자 이상

제공된 AI 동향 정보:

"""
    
    try:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": instruction + text[:12000]
                    }
                ]
            },
            timeout=60.0
        )
        response.raise_for_status()
        
        result = response.json()
        document = result["content"][0]["text"]
        
        return {
            "status": "success",
            "document": document,
            "content": document
        }
        
    except Exception as e:
        return {
            "status": "error",
            "document": "",
            "message": f"Paper generation failed: {str(e)}"
        }
