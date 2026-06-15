"""Synapse FastAPI 엔트리포인트."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.documents import router as documents_router
from app.api.jobs import router as jobs_router
from app.api.search import router as search_router
from app.common import setup_library_logging
from app.config import settings

setup_library_logging()

app = FastAPI(title=settings.project_name)

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


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    return {"status": "ready"}


@app.get("/health")
async def health():
    return {"status": "ok"}
