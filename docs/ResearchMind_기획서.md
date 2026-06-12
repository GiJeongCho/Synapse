# ResearchMind Agent — 프로젝트 기획서

> AI가 논문·뉴스·법령을 스스로 리서치하고, 분석하고, 리포트까지 써주는 Multi-Agent 시스템

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [기술 스택](#2-기술-스택)
3. [Multi-Agent 아키텍처](#3-multi-agent-아키텍처)
4. [전처리 파이프라인 (핵심 특장점)](#4-전처리-파이프라인-핵심-특장점)
5. [중요도 스코어링 & 하이라이팅](#5-중요도-스코어링--하이라이팅)
6. [DB 설계](#6-db-설계)
7. [웹 화면 플로우](#7-웹-화면-플로우)
8. [포트폴리오 차별화 포인트](#8-포트폴리오-차별화-포인트)

---

## 1. 프로젝트 개요

### 한 줄 소개

> 주제를 던지면 AI가 스스로 파고들어 리포트까지 작성해주는 Multi-Agent 리서치 시스템

### 타겟 도메인

| 도메인 | 소스 |
|--------|------|
| 논문 | arXiv API, Semantic Scholar |
| 뉴스 | NewsAPI, RSS |
| 법령 | 국가법령정보 공개 API |

### 목표

- Supervisor 패턴의 Multi-Agent 시스템 설계 및 구현
- Adaptive Chunking 기반 전처리 파이프라인 구축
- Vector DB(Qdrant) + Graph DB(Neo4j) 하이브리드 검색
- HITL(Human-in-the-Loop) 하이라이팅 인터페이스

---

## 2. 기술 스택

| 레이어 | 기술 | 선택 이유 |
|--------|------|-----------|
| Agent 오케스트레이션 | **LangGraph** | 조건부 루프 DAG, Supervisor 패턴 지원 |
| LLM | **Claude API (Sonnet)** | 추론·분석 품질 |
| Vector DB | **Qdrant** | 단일 바이너리, payload 필터 강력, Cloud 1GB 무료 |
| Graph DB | **Neo4j** (AuraDB) | 개념-문서 관계 탐색, Cypher 쿼리, 무료 플랜 |
| 백엔드 | **FastAPI** | async 지원, SSE 스트리밍 |
| 프론트 | **Streamlit** | 빠른 프로토타이핑 |
| PDF 파싱 | **Docling** / PyMuPDF | 구조 인식 파싱 |

> **Qdrant vs Milvus 선택 이유**
> Milvus는 분산 컴포넌트(etcd, MinIO, Pulsar)가 필요해 로컬 세팅이 무겁다.
> 사이드 프로젝트 규모에서는 Docker 한 줄로 끝나는 Qdrant가 압도적으로 적합.
> Milvus는 수백만 벡터 이상 대규모 프로덕션에서 고려.

---

## 3. Multi-Agent 아키텍처

### 구조 개요

```
사용자 (자연어 질문)
        ↓
┌─────────────────────┐
│  Orchestrator Agent  │  ← 전체 지휘관 (추론 + 태스크 분배 + 완료 판단)
└──────────┬──────────┘
           │ 동적 지시 / 결과 수집
     ┌─────┼──────────────┬──────────────┐
     ↓     ↓              ↓              ↓
 Search  Crawl        Graph         Analyst
 Agent   Agent        Agent         Agent
     └─────┴──────────────┴──────────────┘
                                          ↓
                                     Writer Agent
                                     (최종 리포트)
```

### Agent별 역할

| Agent | 역할 | 사용 도구 |
|-------|------|-----------|
| **Orchestrator** | 질문 해석, 태스크 분해, 호출 순서 동적 결정, 완료 판단 | 다른 에이전트 호출 |
| **Search** | Qdrant semantic search, arXiv / 법령 API 쿼리 | Qdrant, 외부 API |
| **Crawl** | 실시간 웹 스크래핑, 뉴스 수집 | Playwright / BeautifulSoup |
| **Graph** | Neo4j 개념-관계 읽기/쓰기, 연결 탐색 | Neo4j Cypher |
| **Analyst** | 수집 정보 분석, 신뢰도 판단, 재수집 여부 결정 | LLM reasoning |
| **Writer** | 최종 리포트 구조화 및 생성 | LLM + template |

### Orchestrator 판단 로직

단순 파이프라인과의 핵심 차이 — Orchestrator는 매 스텝마다 LLM이 직접 판단한다.

```
사용자: "AI 안전 규제 최신 동향 알려줘"

Orchestrator 추론:
  → "법령 + 논문 + 뉴스 다 필요하겠다"         → Search / Crawl 병렬 호출
  → 결과 수신 후: "관계 파악이 필요하다"        → Graph Agent 호출
  → 결과 수신 후: "정보 충분, 작성 가능하다"    → Writer Agent 호출
```

**Orchestrator가 판단하는 시점들**

1. 질문이 단순 사실인지 / 복합 리서치인지 분류 → 하위 태스크 수 결정
2. Relevance score 보고 추가 검색 여부 판단
3. 새 개념이 그래프에 없으면 노드 생성, 있으면 엣지만 추가
4. 정보가 충분한지 판단 → 부족하면 Search Agent에 재요청 (루프)

---

## 4. 전처리 파이프라인 (핵심 특장점)

> 기반 논문: *"Adaptive Chunking: Optimizing Chunking-Method Selection for RAG"* — LREC 2026 채택

### 파이프라인 전체 흐름

```
문서 입력 (PDF / 뉴스 / 법령)
        ↓
[1단계] 문서 타입 분류
        ├── 논문  → LLM Regex Splitter   (섹션 헤딩 패턴 자동 감지)
        ├── 법령  → Split-then-Merge     (조항 단위 강제 분리)
        └── 뉴스  → Recursive Splitter   (역피라미드 구조)
        ↓
[2단계] Adaptive Chunking
        ├── 여러 청커 병렬 실행
        ├── 5가지 내재적 지표로 채점
        └── 문서별 최고점 청커 결과 채택
        ↓
[3단계] 후처리 (크기 정규화)
        ├── 과대 청크 분할 (> 1,100 토큰)
        └── 과소 청크 병합 (< 100 토큰)
        ↓
[4단계] 중요도 스코어링        ← 논문에 없는 차별화 포인트
        ├── 위치 가중치
        ├── LLM 분류
        ├── 인용 밀도
        └── 키워드 밀도
        ↓
[5단계] HITL 검수
        └── 사용자 하이라이팅 조정 → 피드백 저장
        ↓
[6단계] Qdrant 저장
        └── 청크 품질 점수 + 중요도 메타데이터 포함
```

### Adaptive Chunking — 5가지 내재적 지표

논문이 제안하는 품질 지표. 정답(ground-truth) 없이 청크 자체만으로 계산된다.

| 지표 | 전체 이름 | 측정 내용 |
|------|-----------|-----------|
| **RC** | References Completeness | 대명사-개체 쌍이 같은 청크에 온전히 존재하는 비율 |
| **BI** | Block Integrity | 문단/표/그림 등 구조 블록이 깨지지 않은 비율 |
| **ICC** | Intrachunk Cohesion | 청크 내 문장들과 청크 전체 임베딩 간 의미 유사도 |
| **DCC** | Document Contextual Coherence | 청크와 주변 슬라이딩 윈도우 간 유사도 |
| **SC** | Size Compliance | 목표 토큰 범위(100~1,100) 안에 드는 청크 비율 |

> **논문 실험 결과**
> Adaptive Chunking: 종합 평균 **91.07** (단일 청커 최고 89.80 대비 우위)
> RAG 성능: Retrieval Completeness +9.6pp, 답변 정확도 +7.9pp, 답변 가능 질문 수 +32.7%

### 두 가지 새로운 청커 (논문 기반)

**① LLM Regex Splitter**

LLM이 문서 앞부분(8,000 토큰)을 보고 적합한 정규식 패턴 하나를 생성.
이후 해당 패턴을 전체 문서에 `re.split`으로 적용.

- 장점: LLM 유연성 + 결정론적 실행 속도
- 적합: 논문 (섹션 헤딩), 법령 (조항 구분자)

**② Split-then-Merge Recursive Splitter**

1차 패스: 구분자 우선순위(제목→섹션→문장→글자)로 재귀 분할
2차 패스: 인접 조각을 탐욕적으로 병합 (크기 제약 내)

- 장점: 단일 재귀 대비 SC 개선 + 맥락 보존
- 적합: 법령, 서술형 긴 문서

---

## 5. 중요도 스코어링 & 하이라이팅

> 논문이 다루지 않은 영역 — 본 프로젝트의 핵심 차별화 포인트

### 4가지 중요도 레이블

| 레이블 | 색상 | 판단 기준 | 연결 에이전트 | 처리 방식 |
|--------|------|-----------|---------------|-----------|
| **Core** | 🔴 빨강 | 핵심 주장 / 결론 / 핵심 수치 포함 | Search Agent | 우선 임베딩, 검색 가중치 높음 |
| **Support** | 🟡 노랑 | 근거 / 실험 데이터 / 비교 결과 | Analyst Agent | 주장 검증 시 근거 자료 |
| **Context** | 🔵 파랑 | 배경 / 관련 연구 / 정의 | Graph Agent | 개념 노드 연결에 활용 |
| **Noise** | ⬜ 회색 | 감사의 글 / 중복 내용 / 저자 정보 | — | 임베딩 제외 또는 낮은 가중치 |

### 스코어링 기준 상세

```
위치 가중치
  - Abstract, Conclusion 섹션 → 기본 점수 +0.3
  - Introduction, Method → 기본 점수 +0.1
  - Acknowledgement → 기본 점수 -0.5

LLM 분류
  - "이 청크가 핵심 주장을 담고 있는가?" → binary 판단
  - 결과값이 score에 가중 합산

키워드 밀도
  - 도메인 핵심어(사전 정의) 등장 빈도 계산
  - 법령: 조항번호, 의무, 금지 등
  - 논문: propose, outperform, result 등

인용 밀도 (논문 한정)
  - 다른 청크에서 해당 구간을 참조하는 횟수
```

### HITL 하이라이팅 플로우

```
문서 업로드
    ↓
Preprocessing Agent 자동 하이라이팅
    └── 색깔별로 청크 표시된 문서 뷰어 렌더링
    ↓
사용자가 레이블 조정 가능 (HITL)
    └── "이 청크는 Support인데 Core로 바꿔줘"
    ↓
수정된 레이블이 Qdrant payload에 저장
    └── user_adjusted: true 플래그 기록
    ↓
이후 검색 시 사용자 피드백 반영됨
```

---

## 6. DB 설계

### Qdrant Payload 구조

```json
{
  "id": "chunk_arxiv2401_003",
  "vector": ["...임베딩 벡터..."],
  "payload": {
    "text": "본 연구에서 제안하는 방법은...",
    "source": "arxiv_2401.00001",
    "doc_type": "paper",
    "section": "conclusion",

    "chunk_scores": {
      "RC": 0.98,
      "BI": 1.00,
      "ICC": 0.74,
      "DCC": 0.81,
      "SC": 1.00,
      "total": 0.906
    },
    "chunker_used": "llm_regex",

    "importance": "core",
    "importance_score": 0.91,
    "importance_reason": "결론 섹션 + 핵심 수치 포함",
    "user_adjusted": false
  }
}
```

### Neo4j 그래프 구조

```cypher
(Concept:AI안전) -[REFERENCED_IN]→ (Paper:arxiv_001)
(Paper:arxiv_001) -[CITES]→        (Paper:arxiv_002)
(Law:개인정보보호법) -[REGULATES]→  (Concept:AI안전)
(Author:홍길동) -[WROTE]→           (Paper:arxiv_001)
```

### Vector DB / Graph DB 역할 분리

| | **Qdrant (Vector)** | **Neo4j (Graph)** |
|---|---|---|
| 저장 대상 | 논문/뉴스 청크 임베딩 | 개념-논문-저자-법령 관계 |
| 쿼리 방식 | Semantic similarity search | Cypher 관계 탐색 |
| 언제 사용 | "이거랑 비슷한 문서 찾아줘" | "이 개념과 연결된 법령은?" |
| 필터 예시 | `importance: core` 필터링 | `MATCH (c)-[:REGULATES]->(l)` |

---

## 7. 웹 화면 플로우

### 리서치 화면 (메인)

| 화면 | 기능 | 연결 에이전트 |
|------|------|---------------|
| **① 홈/입력** | 자연어 쿼리 + 도메인 필터(논문/뉴스/법령) | Orchestrator 트리거 |
| **② 에이전트 현황** | 실시간 SSE로 각 에이전트 상태 표시 | 전체 에이전트 모니터링 |
| **③ 지식 그래프** | Neo4j 결과 force-directed 시각화 | Graph + Analyst |
| **④ 최종 리포트** | Markdown 렌더링 + MD/PDF 내보내기 | Writer |
| **⑤ 히스토리** | 과거 리서치 목록, 재질문 연결 | — |

### 전처리 / 하이라이팅 화면

| 화면 | 기능 |
|------|------|
| **A. 문서 업로드** | PDF / URL 드래그 업로드 |
| **B. 자동 하이라이팅** | AI가 Core/Support/Context/Noise 자동 분류 |
| **C. HITL 수정 패널** | 레이블 클릭으로 변경, 피드백 저장 |
| **D. 에이전트 매핑 확인** | 레이블별 어떤 에이전트에 연결되는지 표시 |
| **E. 청크 품질 대시보드** | RC/BI/ICC/DCC/SC 5지표 수치 표시 |
| **F. 저장 확인** | 청크 개수, 레이블 분포, 저장 완료 상태 |

---

## 8. 포트폴리오 차별화 포인트

### 기술적 차별화

1. **Supervisor 패턴 Multi-Agent** — LangGraph 조건부 루프 DAG로 Orchestrator가 동적 판단
2. **Adaptive Chunking 구현** — LREC 2026 논문 기반 5지표 청크 품질 평가 시스템
3. **Vector + Graph Hybrid Retrieval** — Qdrant semantic search + Neo4j 관계 탐색 결합
4. **LLM 기반 중요도 스코어링** — 논문이 다루지 않은 영역, 직접 설계
5. **HITL 피드백 루프** — 사용자 하이라이팅 수정이 검색 가중치에 반영

### 포트폴리오 한 줄 설명

> *LREC 2026 채택 논문의 Adaptive Chunking 프레임워크를 구현하고,
> 논문이 다루지 않은 LLM 기반 중요도 스코어링과 HITL 하이라이팅을 결합해
> 검색 정밀도와 사용자 피드백 루프를 동시에 구현한 Multi-Agent 리서치 시스템*

---

*문서 작성일: 2025-06*
