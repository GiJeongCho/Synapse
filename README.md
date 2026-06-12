# Synapse — ResearchMind

> 주제를 던지면 AI가 스스로 파고들어 리포트까지 작성해주는 Multi-Agent 리서치 시스템

논문·뉴스·법령을 자동으로 수집·분석하고, **Adaptive Chunking** 기반 전처리와 **HITL(Human-in-the-Loop) 하이라이팅**을 통해 검색 정밀도를 극대화합니다.

---

## 핵심 특징

- **Supervisor 패턴 Multi-Agent** — LangGraph 기반 Orchestrator가 하위 에이전트(Search, Crawl, Graph, Analyst, Writer)를 동적으로 지휘
- **Adaptive Chunking** — LREC 2026 논문 기반, 여러 청커를 병렬 실행한 뒤 5가지 내재적 지표(RC·BI·ICC·DCC·SC)로 최적 청커를 자동 선택
- **LLM 기반 중요도 스코어링** — 위치 가중치 + 키워드 밀도 + 인용 밀도 + LLM 분류로 Core / Support / Context / Noise 4단계 레이블 부여
- **HITL 하이라이팅** — 색 농도 기반 청크 시각화 + 사용자 레이블 수정 → Qdrant payload에 피드백 반영
- **Vector + Graph Hybrid Retrieval** — Qdrant 시맨틱 검색 + Neo4j 관계 탐색 결합

---

## 기술 스택

| 레이어 | 기술 | 역할 |
|--------|------|------|
| Agent 오케스트레이션 | LangGraph | 조건부 루프 DAG, Supervisor 패턴 |
| LLM | Claude API (Sonnet) | 문서 분류, 중요도 판단, 리포트 생성 |
| Vector DB | Qdrant / Milvus Lite | 청크 임베딩 저장 및 시맨틱 검색 |
| Graph DB | Neo4j (AuraDB) | 개념-문서-저자 관계 탐색 |
| 임베딩 | sentence-transformers | all-MiniLM-L6-v2 (384차원) |
| 백엔드 | FastAPI | async API + SSE 스트리밍 |
| 프론트엔드 | Streamlit | HITL 인터페이스 프로토타입 |
| PDF 파싱 | Docling / PyMuPDF | 구조 인식 문서 파싱 |

---

## 프로젝트 구조

```
Synapse/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── documents.py       # 문서 업로드·조회·편집 API
│   │   │   └── search.py          # RAG 검색 API
│   │   ├── preprocessing/
│   │   │   ├── chunkers/
│   │   │   │   ├── llm_regex.py   # LLM Regex Splitter
│   │   │   │   ├── recursive.py   # Recursive Splitter
│   │   │   │   └── split_merge.py # Split-then-Merge Splitter
│   │   │   ├── classifier.py      # 문서 타입 분류 (paper/news/law)
│   │   │   ├── metrics.py         # 5가지 청크 품질 지표
│   │   │   ├── normalize.py       # 청크 크기 정규화
│   │   │   ├── pipeline.py        # 전처리 파이프라인 오케스트레이터
│   │   │   └── scoring.py         # 중요도 스코어링
│   │   ├── rag/
│   │   │   ├── retriever.py       # 시맨틱 검색
│   │   │   └── reranker.py        # 검색 결과 리랭킹
│   │   ├── vectordb/
│   │   │   └── milvus_client.py   # Vector DB 클라이언트
│   │   ├── config.py              # 설정 관리
│   │   └── main.py                # FastAPI 엔트리포인트
│   └── requirements.txt
├── frontend/
│   └── app.py                     # Streamlit HITL 인터페이스
└── docs/
    ├── ResearchMind_기획서.md
    └── Adaptive_Chunking_논문정리.md
```

---

## 전처리 파이프라인

```
문서 입력 (PDF / 뉴스 / 법령)
       ↓
[1] 문서 타입 분류 — 휴리스틱 + LLM 폴백
       ├── 논문  → LLM Regex Splitter
       ├── 법령  → Split-then-Merge (조항 단위)
       └── 뉴스  → Recursive Splitter
       ↓
[2] Adaptive Chunking — 후보 청커 병렬 실행 → 5지표 채점 → 최고점 채택
       ↓
[3] 크기 정규화 — 과대 청크(>1,100 토큰) 분할, 과소 청크(<100 토큰) 병합
       ↓
[4] 중요도 스코어링 — Core / Support / Context / Noise 분류
       ↓
[5] HITL 검수 — 사용자 하이라이팅 조정
       ↓
[6] 임베딩 + Vector DB 저장
```

### 청크 품질 지표 (5 Intrinsic Metrics)

| 지표 | 전체 이름 | 측정 내용 |
|------|-----------|-----------|
| **RC** | References Completeness | 대명사-개체 쌍이 같은 청크에 온전히 존재하는 비율 |
| **BI** | Block Integrity | 구조 블록(표, 코드, 제목)이 깨지지 않은 비율 |
| **ICC** | Intrachunk Cohesion | 청크 내 문장-청크 전체 임베딩 간 의미 유사도 |
| **DCC** | Document Contextual Coherence | 청크와 주변 슬라이딩 윈도우 간 유사도 |
| **SC** | Size Compliance | 목표 토큰 범위(100~1,100) 안에 드는 비율 |

---

## 시작하기

### 사전 요구사항

- Python 3.10+
- (선택) Anthropic API Key — LLM 기반 분류·스코어링 활성화

### 설치

```bash
git clone https://github.com/GiJeongCho/Synapse.git
cd Synapse

pip install -r backend/requirements.txt
```

### 환경 변수

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
ANTHROPIC_API_KEY=sk-ant-...

# Neo4j (선택)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 실행

```bash
# 백엔드 서버
cd backend
uvicorn app.main:app --reload --port 8000

# 프론트엔드 (새 터미널)
cd frontend
streamlit run app.py
```

### API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 상태 확인 |
| `POST` | `/api/documents/upload` | 문서 업로드 + 전처리 |
| `GET` | `/api/documents/list` | 저장된 문서 목록 |
| `GET` | `/api/documents/chunks/{source}` | 문서별 청크 조회 |
| `POST` | `/api/documents/chunks/edit` | 청크 수정 + 재임베딩 |
| `POST` | `/api/documents/chunks/delete` | 청크 삭제 |
| `POST` | `/api/search/query` | RAG 시맨틱 검색 |

---

## 참고 논문

- **Adaptive Chunking: Optimizing Chunking-Method Selection for RAG** (LREC 2026)
  — 5가지 내재적 품질 지표 기반의 청커 자동 선택 프레임워크

---

## License

MIT
