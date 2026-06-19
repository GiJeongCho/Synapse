"""API endpoints for document upload, listing, chunk viewing, editing, deletion."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.preprocessing.pipeline import reembed_and_upsert, run_pipeline
from app.vectordb.milvus_client import delete_chunks, get_chunks_by_source, list_sources

router = APIRouter()


class ChunkEditRequest(BaseModel):
    chunk_id: str
    new_text: str
    source: str
    doc_type: str = "paper"


class ChunkDeleteRequest(BaseModel):
    chunk_ids: list[str]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document (PDF/text), run the full preprocessing pipeline,
    and store chunks in Milvus."""
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "doc.txt").suffix.lower()
    doc_id = str(uuid.uuid4())[:8]
    save_path = upload_dir / f"{doc_id}{ext}"

    content = await file.read()
    save_path.write_bytes(content)

    # Extract text
    text = _extract_text(save_path, ext)
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    source = file.filename or doc_id
    result = await run_pipeline(text, source=source)

    return {
        "source": result.source,
        "doc_type": result.doc_type,
        "chunker_used": result.chunker_used,
        "num_chunks": len(result.chunks),
        "metrics_summary": result.metrics_summary,
        "extraction_method": "ocr" or "fitz"
    }


def _extract_text(path: Path, ext: str) -> str:
    """Extract plain text from a file.
    PDF: fitz로 먼저 추출 후 품질 낮으면 OCR API로 폴백.
    """
    if ext == ".pdf":
        text = _extract_with_fitz(path)
        if _needs_ocr(text, path):
            ocr_text = _extract_via_ocr(path)
            if ocr_text and ocr_text.strip():
                return ocr_text
        return text
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_with_fitz(path: Path) -> str:
    """fitz(PyMuPDF)로 텍스트 추출."""
    try:
        import fitz
        doc = fitz.open(str(path))
        return "\n\n".join(page.get_text() for page in doc)
    except ImportError:
        return ""


def _needs_ocr(text: str, path: Path) -> bool:
    """OCR이 필요한지 판단."""
    import fitz
    try:
        doc = fitz.open(str(path))
        page_count = max(doc.page_count, 1)
    except Exception:
        page_count = 1

    chars_per_page = len(text.strip()) / page_count

    # 페이지당 100자 미만이면 스캔 PDF로 판단
    if chars_per_page < 100:
        return True

    # 전체 텍스트 200자 미만
    if len(text.strip()) < 200:
        return True

    return False


def _extract_via_ocr(path: Path) -> str:
    """OCR API 호출해서 마크다운 텍스트 반환."""
    import httpx
    from app.config import settings

    url = f"{settings.ocr_api_url.rstrip('/')}/ocr/process"
    try:
        with open(path, "rb") as f:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    url,
                    files={"file": (path.name, f, "application/pdf")},
                )
                resp.raise_for_status()
        result = resp.json()
        # OCR API 응답 키 확인 후 조정 필요
        return result.get("markdown", "") or result.get("text", "") or result.get("content", "")
    except Exception as e:
        return ""


# ---------------------------------------------------------------------------
# List & View
# ---------------------------------------------------------------------------

@router.get("/list")
async def list_documents():
    """List all documents stored in Milvus."""
    return list_sources()


@router.get("/chunks/{source}")
async def get_document_chunks(source: str):
    """Get all chunks for a document, sorted by color_intensity (descending)."""
    chunks = get_chunks_by_source(source)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks.sort(key=lambda c: c.get("color_intensity", 0), reverse=True)
    return chunks


# ---------------------------------------------------------------------------
# Edit & Delete (HITL)
# ---------------------------------------------------------------------------

@router.post("/chunks/edit")
async def edit_chunk(req: ChunkEditRequest):
    """Edit a chunk's text → re-embed → upsert back to Milvus."""
    result = reembed_and_upsert(
        chunk_id=req.chunk_id,
        new_text=req.new_text,
        source=req.source,
        doc_type=req.doc_type,
    )
    return result

@router.post("/reprocess/{source:path}")
async def reprocess_document(source: str):
    """문서 전체를 다시 파이프라인에 돌려 청크/점수를 재계산한다."""
    # 1. 기존 청크 삭제
    existing = get_chunks_by_source(source)
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_ids = [c["id"] for c in existing]
    delete_chunks(chunk_ids)

    # 2. 원본 파일에서 텍스트 재추출
    upload_dir = Path(settings.upload_dir)
    # source가 파일명이므로 업로드 폴더에서 찾기
    candidates = list(upload_dir.glob("*"))
    save_path = next((p for p in candidates if source in p.name), None)

    if save_path is None:
        raise HTTPException(status_code=404, detail="Original file not found")

    ext = save_path.suffix.lower()
    text = _extract_text(save_path, ext)

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    # 3. 전체 파이프라인 재실행
    result = await run_pipeline(text, source=source)

    return {
        "source": result.source,
        "doc_type": result.doc_type,
        "chunker_used": result.chunker_used,
        "num_chunks": len(result.chunks),
        "metrics_summary": result.metrics_summary,
        "reprocessed": True,
    }

@router.post("/chunks/delete")
async def delete_chunk(req: ChunkDeleteRequest):
    """Delete chunks by ID from Milvus."""
    delete_chunks(req.chunk_ids)
    return {"deleted": req.chunk_ids}
