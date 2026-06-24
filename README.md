
## 백엔드 실행
cd ~Synapse/backend
pip install -r requirements.txt    # 최초 1회
uvicorn app.main:app --reload --host 0.0.0.0 --port 2004


## 프론트 실행
cd ~Synapse/frontend
npm install    # 최초 1회
npm run dev


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
