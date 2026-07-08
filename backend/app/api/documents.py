"""API endpoints for document upload, listing, chunk viewing, editing, deletion."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
import re

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.preprocessing.pipeline import reembed_and_upsert, run_pipeline
# from app.vectordb.milvus_client import delete_chunks, get_chunks_by_source, list_sources, drop_all_chunks, delete_chunks_by_source
from app.vectordb.qdrant_client import delete_chunks, get_chunks_by_source, list_sources, drop_all_chunks, delete_chunks_by_source

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
    text, extraction_method = _extract_text(save_path, ext)
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    source = file.filename or doc_id
    result = await run_pipeline(text, source=source)

    return {
        "source": result.source,
        "doc_type": result.doc_type,
        "extraction_method": extraction_method,
        "chunker_used": result.chunker_used,
        "num_chunks": len(result.chunks),
        "metrics_summary": result.metrics_summary,
        "all_chunker_metrics": result.all_chunker_metrics,
    }


def _clean_text(text: str) -> str:
    """PDF 추출 시 섞인 정규식 메타문자 제거."""
    text = re.sub(r'\\s\*', '', text)
    text = re.sub(r'\\d\+', '', text)
    text = re.sub(r'\\n', '\n', text)
    text = re.sub(r'\\s', ' ', text)
    return text.strip()


def _extract_text(path: Path, ext: str) -> tuple[str, str]:
    if ext == ".pdf":
        text = _extract_with_fitz(path)
        if _needs_ocr(text):
            ocr_text = _extract_via_ocr(path)
            if ocr_text:
                return _clean_text(ocr_text), "ocr"
        return _clean_text(text), "fitz"
    elif ext == ".docx":
        return _clean_text(_extract_with_docx(path)), "docx"
    return _clean_text(path.read_text(encoding="utf-8", errors="replace")), "plaintext"

def _extract_with_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        texts = []
        # 일반 단락
        for para in doc.paragraphs:
            if para.text.strip():
                texts.append(para.text)
        # 표 내용도 추출
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells if cell.text.strip()
                )
                if row_text:
                    texts.append(row_text)
        return "\n\n".join(texts)
    except Exception:
        return ""


def _extract_with_fitz(path: Path) -> str:
    """fitz(PyMuPDF)로 텍스트 추출."""
    try:
        import fitz
        doc = fitz.open(str(path))
        return "\n\n".join(page.get_text() for page in doc)
    except Exception:
        return ""


def _needs_ocr(text: str) -> bool:
    """텍스트 품질이 낮으면 OCR 필요 판단."""
    if not text or len(text.strip()) < 100:
        return True
    garbled = text.count("\ufffd")  # 깨진 문자(?) 개수
    if len(text) > 0 and garbled / len(text) > 0.05:
        return True
    return False


def _extract_via_ocr(path: Path) -> str:
    """외부 OCR API 호출 → 마크다운 텍스트 반환."""
    import httpx
    try:
        with open(path, "rb") as f:
            resp = httpx.post(
                f"{settings.ocr_api_url}/ocr/process",
                files={"file": (path.name, f, "application/pdf")},
                timeout=120.0,
            )
        resp.raise_for_status()
        data = resp.json()
        return data.get("markdown", data.get("text", ""))
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# List & View
# ---------------------------------------------------------------------------

@router.get("/list")
async def list_documents():
    """List all documents stored in Milvus."""
    return list_sources()


@router.get("/graph/{source}")
async def get_document_graph(source: str):
    """Get the Neo4j graph structure (nodes + edges) for a document."""
    from app.services.rag.graph_store import graph_store
    return graph_store.get_document_graph(source=source)


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


@router.post("/chunks/delete")
async def delete_chunk(req: ChunkDeleteRequest):
    """Delete chunks by ID from Milvus."""
    delete_chunks(req.chunk_ids)
    return {"deleted": req.chunk_ids}

@router.delete("/all")
async def delete_all_documents():
    """Milvus + Neo4j 전체 데이터 삭제."""
    from app.services.rag.graph_store import graph_store
    drop_all_chunks()
    graph_store.delete_all()
    return {"deleted": "all"}


@router.delete("/{source}")
async def delete_document(source: str):
    from app.services.rag.graph_store import graph_store
    chunks = get_chunks_by_source(source)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_chunks_by_source(source)
    graph_store.delete_document_and_chunks(source)
    return {"deleted": source, "num_chunks": len(chunks)}