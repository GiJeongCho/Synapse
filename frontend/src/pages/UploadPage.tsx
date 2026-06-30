import { useEffect, useRef, useState } from "react";
import {
  deleteDocument,
  getDocumentChunks,
  listDocuments,
  uploadDocument,
} from "../api/client";
import type { DocumentItem, UploadResult } from "../types";

const DOC_TYPE_COLOR: Record<string, string> = {
  law: "#4f7cff",
  paper: "#7c5cff",
  news: "#ff7c4f",
  unknown: "#9aa1b1",
};

const IMPORTANCE_COLOR: Record<string, string> = {
  core: "#4f7cff",
  support: "#22c55e",
  context: "#f59e0b",
  noise: "#9aa1b1",
};

interface DocInfo {
  source: string;
  doc_type: string;
  num_chunks: number;
  chunker_used: string;
  avg_score: number;
  importance_counts: Record<string, number>;
}

/** 삭제 확인 모달 */
function DeleteModal({
  source,
  onConfirm,
  onCancel,
}: {
  source: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 14,
          padding: "28px 32px",
          maxWidth: 420,
          width: "90%",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <p style={{ fontSize: "1.3rem", margin: "0 0 10px" }}>🗑️ 문서 삭제</p>
        <p style={{ color: "var(--muted)", marginBottom: 6, fontSize: "0.9rem" }}>
          아래 문서를 삭제하시겠습니까?
        </p>
        <p
          style={{
            background: "rgba(255,79,79,0.08)",
            border: "1px solid rgba(255,79,79,0.3)",
            borderRadius: 8,
            padding: "8px 12px",
            fontSize: "0.88rem",
            wordBreak: "break-all",
            marginBottom: 20,
            color: "#ff7070",
          }}
        >
          {source}
        </p>
        <p className="muted" style={{ fontSize: "0.82rem", marginBottom: 20 }}>
          Milvus 벡터 DB와 Neo4j 그래프 DB에서 모든 청크가 영구 삭제됩니다.
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button className="secondary" onClick={onCancel}>
            취소
          </button>
          <button
            style={{ background: "#dc2626" }}
            onClick={onConfirm}
          >
            삭제
          </button>
        </div>
      </div>
    </div>
  );
}

export default function UploadPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deletingSource, setDeletingSource] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [docInfo, setDocInfo] = useState<DocInfo | null>(null);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchDocs();
  }, []);

  async function fetchDocs() {
    try {
      const list = await listDocuments();
      setDocs(list);
    } catch {
      // 서버 미연결 시 무시
    }
  }

  async function handleFile(file: File) {
    setUploading(true);
    setUploadResult(null);
    setError(null);
    setSelectedSource(null);
    setDocInfo(null);
    try {
      const res = await uploadDocument(file);
      setUploadResult(res);
      await fetchDocs();
      // 업로드한 문서 자동 선택
      setSelectedSource(res.source);
      setDocInfo({
        source: res.source,
        doc_type: res.doc_type,
        num_chunks: res.num_chunks,
        chunker_used: res.chunker_used,
        avg_score: res.metrics_summary?.total ?? 0,
        importance_counts: {},
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "업로드 실패";
      setError(msg);
    } finally {
      setUploading(false);
    }
  }

  async function selectDoc(source: string, docType: string) {
    if (selectedSource === source) {
      setSelectedSource(null);
      setDocInfo(null);
      return;
    }
    setSelectedSource(source);
    setDocInfo(null);
    setLoadingInfo(true);
    try {
      const chunks = (await getDocumentChunks(source)) as Record<string, unknown>[];
      const counts: Record<string, number> = {};
      let scoreSum = 0;
      for (const c of chunks) {
        const imp = (c.importance as string) ?? "context";
        counts[imp] = (counts[imp] ?? 0) + 1;
        scoreSum += (c.importance_score as number) ?? 0;
      }
      setDocInfo({
        source,
        doc_type: docType,
        num_chunks: chunks.length,
        chunker_used: (chunks[0]?.chunker_used as string) ?? "-",
        avg_score: chunks.length > 0 ? scoreSum / chunks.length : 0,
        importance_counts: counts,
      });
    } catch {
      setDocInfo(null);
    } finally {
      setLoadingInfo(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    const source = deleteTarget;
    setDeleteTarget(null);
    setDeletingSource(source);
    try {
      await deleteDocument(source);
      setDocs((prev) => prev.filter((d) => d.source !== source));
      if (selectedSource === source) {
        setSelectedSource(null);
        setDocInfo(null);
      }
      if (uploadResult?.source === source) setUploadResult(null);
    } catch {
      alert("삭제 실패");
    } finally {
      setDeletingSource(null);
    }
  }

  return (
    <div>
      {/* 삭제 확인 모달 */}
      {deleteTarget && (
        <DeleteModal
          source={deleteTarget}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      <h2>문서 업로드</h2>
      <p className="muted" style={{ marginTop: -8, marginBottom: 24 }}>
        PDF · DOCX · TXT 파일을 업로드하면 전처리 파이프라인이 자동으로 실행됩니다.
      </p>

      {/* 드롭존 */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${dragging ? "var(--accent)" : "var(--border)"}`,
          borderRadius: 12,
          padding: "40px 24px",
          textAlign: "center",
          cursor: uploading ? "not-allowed" : "pointer",
          background: dragging ? "rgba(79,124,255,0.06)" : "transparent",
          transition: "all 0.15s",
          marginBottom: 24,
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          style={{ display: "none" }}
          onChange={onInputChange}
          disabled={uploading}
        />
        {uploading ? (
          <p style={{ color: "var(--accent)", margin: 0 }}>⏳ 처리 중...</p>
        ) : (
          <>
            <p style={{ fontSize: "2rem", margin: "0 0 8px" }}>📄</p>
            <p style={{ margin: 0 }}>클릭하거나 파일을 드래그하세요</p>
            <p className="muted" style={{ fontSize: "0.82rem", marginTop: 6 }}>PDF · DOCX · TXT</p>
          </>
        )}
      </div>

      {/* 에러 */}
      {error && (
        <div className="card" style={{ borderColor: "#ff4f4f", marginBottom: 16 }}>
          <p style={{ color: "#ff4f4f", margin: 0 }}>❌ {error}</p>
        </div>
      )}

      {/* 업로드 직후 결과 (전체 metrics 포함) */}
      {uploadResult && !selectedSource && (
        <div className="card" style={{ marginBottom: 24, borderColor: "var(--accent)" }}>
          <div className="row" style={{ marginBottom: 12 }}>
            <span style={{ fontWeight: 600 }}>✅ {uploadResult.source}</span>
            <span className="badge" style={{ background: DOC_TYPE_COLOR[uploadResult.doc_type] ?? "#9aa1b1", marginLeft: "auto" }}>
              {uploadResult.doc_type}
            </span>
          </div>
          <div className="stat-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 12 }}>
            <div className="stat"><div className="num">{uploadResult.num_chunks}</div><div className="label">청크 수</div></div>
            <div className="stat"><div className="num">{uploadResult.extraction_method}</div><div className="label">추출 방식</div></div>
            <div className="stat"><div className="num">{uploadResult.chunker_used}</div><div className="label">청커</div></div>
          </div>
          <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
            <strong style={{ color: "var(--text)" }}>품질 점수</strong>
            <div style={{ display: "flex", gap: 16, marginTop: 6, flexWrap: "wrap" }}>
              {Object.entries(uploadResult.metrics_summary).map(([k, v]) => (
                <span key={k}>
                  <span style={{ color: "var(--text)" }}>{k}</span>{" "}
                  {typeof v === "number" ? v.toFixed(3) : v}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 문서 선택 시 상세 정보 카드 */}
      {selectedSource && (
        <div className="card" style={{ marginBottom: 24, borderColor: DOC_TYPE_COLOR[docInfo?.doc_type ?? ""] ?? "var(--border)" }}>
          {loadingInfo ? (
            <p className="muted" style={{ margin: 0 }}>정보 로딩 중...</p>
          ) : docInfo ? (
            <>
              <div className="row" style={{ marginBottom: 12 }}>
                <span style={{ fontWeight: 600, wordBreak: "break-all", flex: 1 }}>{docInfo.source}</span>
                <span className="badge" style={{ background: DOC_TYPE_COLOR[docInfo.doc_type] ?? "#9aa1b1", flexShrink: 0 }}>
                  {docInfo.doc_type}
                </span>
              </div>
              <div className="stat-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 14 }}>
                <div className="stat"><div className="num">{docInfo.num_chunks}</div><div className="label">청크 수</div></div>
                <div className="stat"><div className="num">{docInfo.chunker_used}</div><div className="label">청커</div></div>
                <div className="stat"><div className="num">{docInfo.avg_score.toFixed(3)}</div><div className="label">평균 점수</div></div>
              </div>
              {Object.keys(docInfo.importance_counts).length > 0 && (
                <div>
                  <p style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>
                    <strong>중요도 분포</strong>
                  </p>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {(["core", "support", "context", "noise"] as const).map((level) => {
                      const count = docInfo.importance_counts[level] ?? 0;
                      if (count === 0) return null;
                      return (
                        <div
                          key={level}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 5,
                            background: "rgba(0,0,0,0.2)",
                            borderRadius: 6,
                            padding: "4px 10px",
                            border: `1px solid ${IMPORTANCE_COLOR[level]}44`,
                          }}
                        >
                          <div style={{ width: 8, height: 8, borderRadius: 2, background: IMPORTANCE_COLOR[level], flexShrink: 0 }} />
                          <span style={{ fontSize: "0.82rem", color: "var(--muted)" }}>{level}</span>
                          <span style={{ fontSize: "0.88rem", fontWeight: 600, color: IMPORTANCE_COLOR[level] }}>{count}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="muted" style={{ margin: 0 }}>정보를 불러올 수 없습니다.</p>
          )}
        </div>
      )}

      {/* 업로드된 문서 목록 */}
      <h3 style={{ marginBottom: 12 }}>업로드된 문서 ({docs.length})</h3>
      {docs.length === 0 ? (
        <div className="card">
          <p className="muted" style={{ margin: 0 }}>업로드된 문서가 없습니다.</p>
        </div>
      ) : (
        docs.map((doc) => (
          <div
            key={doc.source}
            className="card row"
            style={{
              marginBottom: 8,
              cursor: "pointer",
              borderColor: selectedSource === doc.source ? (DOC_TYPE_COLOR[doc.doc_type] ?? "var(--accent)") : "var(--border)",
              background: selectedSource === doc.source ? "rgba(79,124,255,0.05)" : "var(--panel)",
              transition: "border-color 0.15s, background 0.15s",
            }}
            onClick={() => selectDoc(doc.source, doc.doc_type)}
          >
            <span
              className="badge"
              style={{ background: DOC_TYPE_COLOR[doc.doc_type] ?? "#9aa1b1", flexShrink: 0 }}
            >
              {doc.doc_type}
            </span>
            <span style={{ flex: 1, wordBreak: "break-all", fontSize: "0.9rem" }}>
              {doc.source}
            </span>
            <button
              className="secondary"
              style={{ flexShrink: 0, padding: "5px 12px", fontSize: "0.82rem" }}
              onClick={(e) => {
                e.stopPropagation();
                setDeleteTarget(doc.source);
              }}
              disabled={deletingSource === doc.source}
            >
              {deletingSource === doc.source ? "삭제 중..." : "삭제"}
            </button>
          </div>
        ))
      )}
    </div>
  );
}
