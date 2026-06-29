# Synapse — Multi-Agent 리서치 시스템

> 주제를 던지면 AI가 스스로 파고들어 리포트까지 작성하는 Multi-Agent 리서치 플랫폼

프로젝트명: **synapse** · 프론트: **React (Vite + TS)** · 백엔드: **FastAPI + LangGraph**

---

## 현재 상태

| 영역 | 상태 |
|------|------|
| 전처리 / 문서 API / RAG 검색 | 기존 구현 유지 (`preprocessing/`, `api/documents`, `api/search`) |
| 에이전트 / Supervisor 워크플로우 | **폴더 골격만** — 기획 확정 후 구현 |
| React UI | **라우팅 셸 + placeholder** — 화면 기획 전 |

**Meta-Agent 아키텍처**: [`docs/agent.md`](docs/agent.md)  
**폴더 구조 상세**: [`docs/project-structure.md`](docs/project-structure.md)  
**에이전트 코딩 표준**: [`docs/agent-development-standards-v2.md`](docs/agent-development-standards-v2.md)

---

## 레포 구조 (요약)

```
Synapse/
├── backend/app/
│   ├── api/              # REST · Job 접수
│   ├── workflows/        # Supervisor (예: research/)
│   ├── agents/           # search / crawl / graph / analyst / writer
│   ├── services/         # RAG · workers · jobs
│   ├── tools/            # LangChain tools
│   ├── core/             # config · LLM · errors
│   ├── preprocessing/    # Adaptive Chunking
│   └── vectordb/         # Milvus
├── frontend/src/         # React (pages · components · api · hooks)
└── docs/
```

---

## 에이전트 시스템

Synapse의 핵심은 **요구사항을 던지면 그에 맞는 하위 에이전트(Child Agent)를 스스로 생성·검증·배포하는 Meta-Agent**입니다. 정해진 에이전트를 실행만 하는 게 아니라, **에이전트를 만드는 에이전트**라는 점이 차별점입니다.

> 상세 설계·다이어그램·State 초안은 [`docs/agent.md`](docs/agent.md) 참고.

### 1. 쌍방 Supervisor 진화 루프

두 Supervisor가 서로의 산출물과 평가 기준을 평가·수정하며 합의에 도달합니다. 단순 재시도(retry)와 달리 **전략과 평가 기준이 동시에 진화**합니다.

| Supervisor | 역할 |
|------------|------|
| **A (Builder)** | 에이전트를 생성하고, 전략을 세우고, B의 평가를 역평가(기준 수정 제안) |
| **B (Critic)** | A의 결과를 평가하고, 개선안을 제시하고, 평가 기준을 관리 |

```
Supervisor-A (Builder)          Supervisor-B (Critic)
  에이전트 생성 ──────────→
                               ←── 평가 + 개선안
  개선안 반영 + 재생성
  + "B의 기준이 너무 엄격" ──→
                               ←── 기준 수정 + 재평가
  ... 합의할 때까지 반복 (max 5라운드)
```

| | 단순 재시도 | 쌍방 진화 |
|---|---|---|
| 뭘 바꾸나 | 같은 전략 반복 | **전략 자체**를 변경 |
| 평가 기준 | 고정 | 평가 기준도 **수정 대상** |
| 방향 | 일방향 | **쌍방향** (서로 평가·수정) |

### 2. 에이전트 생성 파이프라인 (4개 노드)

Supervisor-A가 호출하는 생성 파이프라인은 4단계로 구성됩니다.

```
[1] Requirements Analyzer → [2] Tool Retriever → [3] Environment Provisioner → [4] Evaluator
       요구사항 분석              MCP 도구 검색            실행 환경 구성             샌드박스 테스트
```

| 노드 | 역할 | 핵심 연동 |
|------|------|-----------|
| **Requirements Analyzer** | 요구사항 → 에이전트 페르소나·목표·제약 정의 | — |
| **Tool & Context Retriever** | 필요한 MCP 서버/API 탐색 | **Knowledge Graph(Neo4j) + Vector DB** RAG |
| **Environment Provisioner** | 실행 가능한 프로젝트 패키징 | **uv**(`pyproject.toml`) + **Docker**(`Dockerfile`) |
| **Evaluator** | 더미 입력으로 도구 호출 검증 + Self-Correction | 샌드박스 (실패 시 최대 3회 재시도) |

- **MCP**를 표준 연결 규격으로 사용해 각 에이전트가 외부 인프라·데이터와 소통합니다.
- 실패 정책: 파이프라인 내 `MAX_ITERATION = 3`, 라운드 간 `MAX_ROUNDS = 5`. 한도 초과는 에러가 아니라 **현재까지 최선의 결과로 graceful 종료**.

### 3. 리서치 도메인 에이전트

Meta-Agent와 별개로, 리서치 워크플로우는 Supervisor가 아래 워커 에이전트들을 조율합니다 (`app/agents/`).

| 에이전트 | 역할 | 예상 아키텍처 |
|----------|------|---------------|
| `search_agent` | 벡터/하이브리드 검색 | search → filter → organize → evaluate (루프) |
| `crawl_agent` | 웹·외부 소스 수집 | fetch → extract → normalize (선형) |
| `graph_agent` | Neo4j 관계 탐색 | expand → summarize (선형) |
| `analyst_agent` | 수집 자료 종합 분석 | analyze → critique (루프) |
| `writer_agent` | 최종 리포트 작성 | planner → drafting → evaluation (루프) |

### 4. 구현 표준 (요약)

모든 에이전트는 [`docs/agent-development-standards-v2.md`](docs/agent-development-standards-v2.md)의 **7대 공통 규약**을 따릅니다.

1. 그래프는 `StateGraph` → `compile()`, 팩토리 함수 `create_<agent>_workflow()`
2. State는 `TypedDict`(+`job_id`), 노드는 **변경된 키만** 반환
3. 노드는 `async def node(state, config: RunnableConfig)` 시그니처
4. 프롬프트는 `ChatPromptTemplate`로 `prompts.py`에 분리
5. LLM은 `get_llm_for_agent()` → `await llm.ainvoke(messages)`
6. LLM JSON 응답은 `extract_json_from_llm_response()`로 파싱
7. 모든 I/O는 `async`/`await`, 장기 작업은 `check_if_canceled()`로 취소 확인

> 현재 `agents/` · `workflows/`는 **폴더 골격 단계**이며, 위 설계를 기준으로 기획 확정 후 구현합니다.

---

## 🚀 시작하기 (Getting Started)

### 사전 요구사항

| 항목 | 버전 |
|------|------|
| Python | 3.10 이상 |
| Node.js | 18 LTS 이상 (프론트엔드) |
| npm | 9 이상 |

선택 사항:

- **Anthropic API Key** — LLM 기반 문서 분류·스코어링
- **Docker / Docker Compose** — Neo4j 로컬 실행 시

### 1. 저장소 클론

```bash
git clone https://github.com/GiJeongCho/Synapse.git
cd Synapse
```

### 2. 환경 변수 설정

프로젝트 **루트**에 `.env` 파일을 만듭니다.

```bash
cp .env.example .env
```

`.env` 를 열어 최소한 아래 값을 채웁니다.

```env
# LLM (선택 — 없으면 휴리스틱 폴백 동작)
ANTHROPIC_API_KEY=sk-ant-...

# Vector DB (기본값: backend/synapse.db — Milvus Lite 로컬 파일)
MILVUS_URI=./backend/synapse.db
MILVUS_COLLECTION=synapse_chunks

# Graph DB (선택 — docker-compose 로 Neo4j 기동 시)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

프론트엔드 전용 설정이 필요하면 `frontend/.env` 도 추가할 수 있습니다 (대부분은 Vite 프록시만으로 충분).

```bash
cp frontend/.env.example frontend/.env
# VITE_API_BASE=   # 비우면 dev 서버가 /api, /v1 을 :8000 으로 프록시
```

### 3. 백엔드 설정 및 실행

```bash
cd backend

# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화
# Linux / macOS:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# 의존성 설치
pip install -U pip
pip install -r requirements.txt

# 서버 실행 (프로젝트 루트의 .env 를 자동 로드)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

동작 확인:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. 프론트엔드 설정 및 실행

**새 터미널**에서:

```bash
cd frontend

npm install
npm run dev
```

브라우저: [http://localhost:5173](http://localhost:5173)

개발 모드에서는 Vite 가 `/api`, `/v1` 요청을 `http://localhost:8000` 으로 프록시합니다. **백엔드를 먼저 띄운 뒤** 프론트를 실행하세요.

프로덕션 빌드:

```bash
npm run build
npm run preview
```

### 5. (선택) Neo4j 로컬 실행

그래프 DB 연동 개발 시:

```bash
# 프로젝트 루트에서
docker compose up -d neo4j
```

- Browser UI: [http://localhost:7474](http://localhost:7474)
- Bolt: `bolt://localhost:7687`
- `.env` 의 `NEO4J_PASSWORD` 를 `docker-compose.yml` 의 `NEO4J_AUTH` 와 맞춥니다.

### 6. 자주 쓰는 API

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 상태 |
| `POST` | `/api/documents/upload` | 문서 업로드 + 전처리 |
| `GET` | `/api/documents/list` | 문서 목록 |
| `POST` | `/api/search/query` | RAG 검색 |

### 문제 해결

| 증상 | 확인 |
|----------|------|
| `ModuleNotFoundError: app` | `backend/` 디렉터리에서 uvicorn 실행했는지 확인 |
| 프론트에서 API 연결 실패 | 백엔드 `:8000` 실행 여부, CORS/프록시 확인 |
| LLM 분류 미동작 | `.env` 의 `ANTHROPIC_API_KEY` 설정 |
| Neo4j 연결 실패 | `docker compose ps`, `NEO4J_*` 값 일치 여부 |

---

## License

MIT
