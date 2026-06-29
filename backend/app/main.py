"""Synapse FastAPI 엔트리포인트."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.documents import router as documents_router
from app.api.jobs import router as jobs_router
from app.api.meta_agent import router as meta_agent_router
from app.api.schedules import router as schedules_router
from app.api.search import router as search_router
<<<<<<< HEAD

from app.services.rag.bm25_store import bm25_store
from app.vectordb.milvus_client import list_sources, get_chunks_by_source

=======
from app.api.tools import router as tools_router
from app.api.workflows import router as workflows_router
>>>>>>> fish
from app.common import setup_library_logging
from app.config import settings

setup_library_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.mcp.tool_runtime import ensure_shared_tools
    from app.services.scheduler.engine import startup, shutdown
    ensure_shared_tools()
    startup()
    yield
    shutdown()


app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router, prefix="/v1/agent/execute", tags=["agents"])
app.include_router(jobs_router, prefix="/v1/agent/jobs", tags=["jobs"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(search_router, prefix="/api/search", tags=["search"])
app.include_router(meta_agent_router, prefix="/api/meta-agent", tags=["meta-agent"])
app.include_router(schedules_router, prefix="/api/schedules", tags=["schedules"])
app.include_router(tools_router, prefix="/api/tools", tags=["tools"])
app.include_router(workflows_router, prefix="/api/workflows", tags=["workflows"])


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    return {"status": "ready"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def build_bm25_index():
    sources = list_sources()
    all_chunks = []
    for s in sources:
        chunks = get_chunks_by_source(s["source"])
        all_chunks.extend(chunks)
    bm25_store.build(all_chunks)
    print(f"BM25 인덱스 빌드 완료: {len(all_chunks)}개 청크")