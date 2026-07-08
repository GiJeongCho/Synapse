# Synapse — Multi-Agent 리서치 & 자동화 플랫폼

> 주제를 던지면 AI가 스스로 파고들어 리포트까지 작성하고, 말로 요청하면 **그 일을 대신 해주는 자동화 에이전트를 직접 만들어주는** Multi-Agent 플랫폼

> 👉 **처음 쓰시나요?** [`docs/시작_가이드.md`](docs/시작_가이드.md) 를 보세요. 설치 → 말로 에이전트 만들기 → 메일 받기까지 단계별로 안내합니다.

프로젝트명: **synapse** · 프론트: **React (Vite + TS)** · 백엔드: **FastAPI + LangGraph**

---

## 현재 상태

| 영역 | 상태 |
|------|------|
| 전처리 / 문서 API / RAG 검색 | **구현 완료** (`preprocessing/`, `api/documents`, `api/search`) |
| Meta-Agent (에이전트를 만드는 에이전트) | **구현 완료** — 요청 → 실행 가능한 MCP 도구 생성 → 등록 |
| Meta-Supervisor (쌍방 진화 루프) | **구현 완료** — Solo(1회) / Dual(Builder↔Critic, 자가개선) 모드 |
| 스케줄러 / 도구 청소부 / 하네스 | **구현 완료** (`services/scheduler`, `services/mcp/tool_janitor.py`, `agents/meta_agent/harness.py`) |
| 리서치 워크플로 (Supervisor ↔ 5개 워커) | **구현 완료** — `search / crawl / graph / analyst / writer` |
| React UI | **구현 완료** — 업로드/뷰어/검색/에이전트 생성·관리·흐름도/도구/스케줄 페이지 |
| GraphDB 하이브리드 검색, JWT 인증 | **부분 구현 / 스텁** — 상세는 `docs/구현_현황.md` §5 참고 |

**실행·환경 상세(가장 최신)**: [`docs/구현_현황.md`](docs/구현_현황.md)  
**Meta-Agent 아키텍처(설계 원안)**: [`docs/agent.md`](docs/agent.md)  

**폴더 구조 상세**: [`docs/project-structure.md`](docs/project-structure.md)  
**에이전트 코딩 표준**: [`docs/agent-development-standards-v2.md`](docs/agent-development-standards-v2.md)

---

## 레포 구조 (요약)

```
Synapse/
├── backend/app/
│   ├── api/                  # REST · Job 접수 (meta_agent · tools · schedules · workflows · documents · search)
│   ├── workflows/research/   # Supervisor ↔ 5개 워커 오케스트레이션
│   ├── agents/
│   │   ├── meta_agent/       # 요구사항→도구 검색→코드 생성→평가 (4노드 파이프라인)
│   │   ├── meta_supervisor/  # Builder ↔ Critic 쌍방 진화 루프 (Solo/Dual)
│   │   └── {search,crawl,graph,analyst,writer}_agent/  # 리서치 워커
│   ├── services/
│   │   ├── mcp/              # 도구 런타임·레지스트리·청소부(tool_janitor)
│   │   ├── scheduler/        # APScheduler 기반 cron 등록/실행
│   │   ├── agent_registry/   # 생성된 에이전트 CRUD + 유사도 매칭
│   │   ├── rag/              # vector_store · graph_store · retriever · reranker
│   │   └── jobs/, workers/   # Job 상태, 워커 진입점
│   ├── core/                 # config · LLM 어댑터 · errors · enums
│   ├── preprocessing/        # Adaptive Chunking (분류→청킹→정규화→스코어링)
│   └── vectordb/             # Milvus 클라이언트
├── frontend/src/
│   ├── pages/                # Upload/Viewer/Search/AgentDashboard/AgentCreate/AgentFlow/Tools/Schedules
│   └── components/flow/      # React Flow 기반 그래프 시각화
└── docs/
```

---

## 에이전트 시스템

Synapse의 핵심은 **요구사항을 던지면 그에 맞는 하위 에이전트(실행 가능한 MCP 도구)를 스스로 생성·검증·등록하는 Meta-Agent** 입니다. 정해진 에이전트를 실행만 하는 게 아니라, **에이전트를 만드는 에이전트**라는 점이 차별점입니다.

> 설계 배경·다이어그램은 [`docs/agent.md`](docs/agent.md), **실제 동작 방식**은 [`docs/구현_현황.md`](docs/구현_현황.md)를 따릅니다 (설계 원안과 세부 구현이 일부 다릅니다 — 예: 프로비저닝은 Docker/uv 대신 subprocess 기반 도구 런타임으로 구현).

### 1. 사용 흐름

```
1) 에이전트 생성   → Meta-Agent가 실행 가능한 MCP 도구(Python 파일)를 생성·저장
2) 필수 설정 확인 → SMTP/API 키 등 prereq 체크
3) 실행           → (A) 즉시 실행 버튼  또는  (B) 스케줄(cron) 등록 → 자동 실행
```

> ⚠️ 스케줄 등록은 현재 **사람이 수동으로** 해야 합니다 (자동 cron 등록은 `docs/구현_현황.md` §8 TODO).

### 2. Meta-Supervisor — Solo / Dual 두 모드

| 모드 | 동작 |
|------|------|
| **Solo** | 빠르게 1회 생성. 검증(dry-run) 없이 바로 등록 |
| **Dual (Critic 모드)** | Builder가 생성 직후 **실제 dry-run 실행** → Critic이 결과를 평가 → 실패 시 개선안 반영해 재생성 (`max_rounds=2`) |

### 3. 에이전트 생성 파이프라인 (4개 노드, `agents/meta_agent/`)

```
Requirements Analyzer → Tool Retriever → Provisioner → Evaluator
   요구사항→명세          MCP 도구 검색      실행 코드 생성        더미 입력 검증
```

- **Tool Retriever**: Milvus 기반 MCP 도구 레지스트리(`services/mcp/`)에서 필요한 도구 검색
- **Provisioner**: LLM이 httpx/bs4/smtplib 기반 **실제 실행 코드**를 생성해 `backend/generated_tools/`에 저장
- **Evaluator**: 생성 코드가 규칙(§5.5 `docs/구현_현황.md`)을 지키는지 판정 → 위반 시 재생성 유도

### 4. 안정성 설계 — 다중 안전망

같은 실패를 반복하지 않기 위해 여러 계층을 겹쳐 둡니다 (상세: `docs/구현_현황.md` §5.5~5.6).

| 계층 | 내용 |
|------|------|
| 생성 규칙 | 프롬프트로 인자 기본값·페이로드 절단·다중 소스 폴백 강제 |
| 결정적 보정 | 중복 도구 제거, fetch/발송 도구 누락 시 검증된 표준 도구 자동 주입 |
| 런타임 방어 | 시그니처 기반 인자 바인딩, stdin 전달, 텍스트 절단, 구조화된 에러 보고 |
| Dual 자가개선 | Builder↔Critic이 실제 실행 결과를 보고 평가·재생성 |
| **하네스 2종** | 생성 단계 JSON 파싱 재시도(`agents/meta_agent/harness.py`) + 실행 단계 일시적 실패 재시도(`services/agent_runner.py`) |
| **도구 청소부** | 삭제 시 공용/필수/공유 도구를 하드 규칙 + LLM 심판으로 보호 (`services/mcp/tool_janitor.py`) |

### 5. 리서치 도메인 워커 (`app/agents/`, `app/workflows/research/`)

Meta-Agent와 별개로, 리서치 워크플로는 Supervisor가 아래 워커들을 조율합니다.

| 에이전트 | 역할 |
|----------|------|
| `search_agent` | 벡터/하이브리드 검색 |
| `crawl_agent` | 웹·외부 소스 수집 |
| `graph_agent` | Neo4j 관계 탐색 (현재 GraphStore 검색 미구현 → LLM 기반 대체) |
| `analyst_agent` | 수집 자료 종합 분석 |
| `writer_agent` | 최종 리포트 작성 |

### 6. 구현 표준 (요약)

모든 에이전트는 [`docs/agent-development-standards-v2.md`](docs/agent-development-standards-v2.md)의 **7대 공통 규약**을 따릅니다.

1. 그래프는 `StateGraph` → `compile()`, 팩토리 함수 `create_<agent>_workflow()`
2. State는 `TypedDict`(+`job_id`), 노드는 **변경된 키만** 반환
3. 노드는 `async def node(state, config: RunnableConfig)` 시그니처
4. 프롬프트는 `ChatPromptTemplate`로 `prompts.py`에 분리
5. LLM은 `get_llm_for_agent()` → `await llm.ainvoke(messages)`
6. LLM JSON 응답은 `extract_json_from_llm_response()`로 파싱
7. 모든 I/O는 `async`/`await`, 장기 작업은 `check_if_canceled()`로 취소 확인

---

## 🚀 시작하기 (Getting Started)

### 사전 요구사항

| 항목 | 버전 |
|------|------|
| Python | 3.10 이상 |
| Node.js | 18 LTS 이상 (프론트엔드) |
| npm | 9 이상 |

선택 사항:

- **Anthropic API Key** — LLM 기반 요약·청킹·에이전트 생성 (없으면 대부분 기능 비활성)
- **Gmail SMTP 앱 비밀번호** — 에이전트 메일 발송 기능 사용 시
- **Docker** — Neo4j 로컬 실행 시 (선택, GraphStore 검색 자체는 아직 미구현)

### 1. 저장소 클론

```bash
git clone https://github.com/GiJeongCho/Synapse.git
cd Synapse
```

### 2. 환경 변수 설정

`Synapse/backend/.env` 파일을 새로 만들고 최소한 아래 값을 채웁니다.

```env
# LLM
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-4-5-20251001

# Vector DB / Embedding
MILVUS_URI=backend/synapse.db
MILVUS_COLLECTION=synapse_chunks
EMBED_API_URL=http://ppsystem.kro.kr:5000
RERANK_API_URL=http://ppsystem.kro.kr:5000

# Graph DB (선택)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# SMTP — 에이전트 메일 발송용 (선택, Gmail 앱 비밀번호 필요)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_id@gmail.com
SMTP_PASSWORD=앱_비밀번호_16자리
SMTP_FROM=your_id@gmail.com
```

> **Gmail 앱 비밀번호**: 일반 로그인 비밀번호로는 SMTP 인증 불가.
> [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) 에서 발급한 16자리 사용.

### 3. 백엔드 설정 및 실행

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows PowerShell
# source .venv/bin/activate    # Linux / macOS

# 의존성 설치
pip install -U pip
pip install -r requirements.txt

# 서버 실행 (backend/.env 자동 로드, 포트 2004)
uvicorn app.main:app --reload --host 0.0.0.0 --port 2004
```

동작 확인:

```bash
curl http://localhost:2004/health
# {"status":"ok"}
```

API 문서: [http://localhost:2004/docs](http://localhost:2004/docs)

### 4. 프론트엔드 설정 및 실행

**새 터미널**에서:

```bash
cd frontend
npm install
npm run dev
```

브라우저: [http://localhost:2003](http://localhost:2003) (자동으로 열립니다)

개발 모드에서는 Vite가 `/api`, `/v1` 요청을 `http://localhost:2004`로 프록시합니다. **백엔드를 먼저 띄운 뒤** 프론트를 실행하세요.

프로덕션 빌드:

```bash
npm run build
npm run preview
```

### 5. (선택) Neo4j 로컬 실행

```bash
# 프로젝트 루트에서
docker compose up -d neo4j
```

- Browser UI: [http://localhost:7474](http://localhost:7474)
- Bolt: `bolt://localhost:7687`
- `.env`의 `NEO4J_PASSWORD`를 `docker-compose.yml`의 `NEO4J_AUTH`와 맞춥니다.

### 6. 말로 에이전트 만들기 (5분 요약)

```
1) 위 1~4단계로 백엔드/프론트 실행
2) "에이전트 생성" 메뉴 → 한국어로 요청 입력 (예: "매일 9시에 경제 뉴스 요약해서 메일 보내줘")
3) "에이전트 관리"에서 [실행]으로 1회 테스트 → 메일 도착 확인
4) "스케줄"에서 cron 등록 → 매일 자동 발송
```

> 상세 단계별 가이드는 [`docs/시작_가이드.md`](docs/시작_가이드.md) 참고.

### 7. 자주 쓰는 API

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 상태 |
| `POST` | `/api/documents/upload` | 문서 업로드 + 전처리 |
| `GET` | `/api/documents/list` | 문서 목록 |
| `POST` | `/api/search/query` | RAG 검색 |
| `POST` | `/api/meta-agent/create` | 에이전트 생성 (Solo/Dual) |
| `GET` | `/api/meta-agent/registry` | 생성된 에이전트 목록 |
| `POST` | `/api/meta-agent/registry/{id}/run` | 에이전트 즉시 실행 |
| `POST` | `/api/schedules/register` | 스케줄(cron) 등록 |

전체 엔드포인트 목록은 [`docs/구현_현황.md`](docs/구현_현황.md) §6 참고.

### 문제 해결

| 증상 | 확인 |
|------|------|
| `ModuleNotFoundError: app` | `backend/` 디렉터리에서 uvicorn 실행했는지 확인 |
| 프론트에서 API 연결 실패 | 백엔드 `:2004` 실행 여부, CORS/프록시 확인 |
| `'vite'은(는) 내부 또는 외부 명령...` | `frontend/`에서 `npm install`이 성공했는지 확인 (`node_modules/.bin/vite` 존재 여부) |
| LLM 분류/생성 미동작 | `backend/.env`의 `ANTHROPIC_API_KEY` 설정 |
| 메일이 안 감 | `.env`의 `SMTP_*`(앱 비밀번호 16자리) + 에이전트 상세의 필수 설정 ✓ 확인 |
| Neo4j 연결 실패 | `docker compose ps`, `NEO4J_*` 값 일치 여부 |
 

---

## License

MIT
