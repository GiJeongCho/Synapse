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
    }


def _extract_text(path: Path, ext: str) -> str:
    """Extract plain text from a file."""
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            return "\n\n".join(page.get_text() for page in doc)
        except ImportError:
            raise HTTPException(status_code=500, detail="PyMuPDF not installed")
    elif ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    else:
        return path.read_text(encoding="utf-8", errors="replace")


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


@router.post("/chunks/delete")
async def delete_chunk(req: ChunkDeleteRequest):
    """Delete chunks by ID from Milvus."""
    delete_chunks(req.chunk_ids)
    return {"deleted": req.chunk_ids}
