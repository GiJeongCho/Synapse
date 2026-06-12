"""에이전트 실행 접수 라우터(§15.1) — 기획 확정 후 Job 접수·BackgroundTasks 연동."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import verify_jwt_and_headers

router = APIRouter(dependencies=[Depends(verify_jwt_and_headers)])


# TODO: POST /research 등 — JobResponse 반환, run_research_workflow 백그라운드 실행
