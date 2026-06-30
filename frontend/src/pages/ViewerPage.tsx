import { useEffect, useState } from "react";
import {
  listDocuments,
  getDocumentChunks,
  editChunk,
  deleteChunks,
} from "../api/client";
import type { DocumentItem } from "../types";
import NeovisGraph from "../components/flow/NeovisGraph";

interface Chunk {
  id: string;
  source: string;
  section: string;
  chunker_used: string;
  importance: string;
  importance_score: number;
  color_intensity: number;
  doc_type: string;
  chunk_scores_total: number;
  user_adjusted: boolean;
  text: string;
}

const IMPORTANCE_COLOR: Record<string, string> = {
  core: "#4f7cff",
  support: "#22c55e",
  context: "#f59e0b",
  noise: "#9aa1b1",
};

const IMPORTANCE_DESC: Record<string, string> = {
  core: "핵심 — 문서의 주요 주장·결론이 담긴 청크",
  support: "보조 — 핵심을 뒷받침하는 근거·데이터",
  context: "맥락 — 배경·부연 설명",
  noise: "노이즈 — 검색에 불필요한 내용",
};

function importanceBg(importance: string, intensity: number): string {
  const base = IMPORTANCE_COLOR[importance] ?? "#9aa1b1";
  const alpha = Math.round(intensity * 0.25 * 255)
    .toString(16)
    .padStart(2, "0");
  return `${base}${alpha}`;
}

type ViewMode = "chunks" | "graph";

export default function ViewerPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [savingId, setSavingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("chunks");

  useEffect(() => {
    listDocuments().then(setDocs).catch(() => {});
  }, []);

  async function selectDoc(source: string) {
    setSelectedSource(source);
    setEditingId(null);
    setViewMode("chunks");
    setLoadingChunks(true);
    try {
      const data = await getDocumentChunks(source);
      setChunks(data as unknown as Chunk[]);
    } catch {
      setChunks([]);
    } finally {
      setLoadingChunks(false);
    }
  }

  function startEdit(chunk: Chunk) {
    setEditingId(chunk.id);
    setEditText(chunk.text);
  }

  async function saveEdit(chunk: Chunk) {
    if (editText.trim() === chunk.text) {
      setEditingId(null);
      return;
    }
    setSavingId(chunk.id);
    try {
      await editChunk(chunk.id, editText, chunk.source, chunk.doc_type);
      setChunks((prev) =>
        prev.map((c) =>
          c.id === chunk.id
            ? { ...c, text: editText, user_adjusted: true }
            : c,
        ),
      );
      setEditingId(null);
    } catch {
      alert("저장 실패");
    } finally {
      setSavingId(null);
    }
  }

  async function handleDelete(chunkId: string) {
    if (!confirm("이 청크를 삭제하시겠습니까?")) return;
    setDeletingId(chunkId);
    try {
      await deleteChunks([chunkId]);
      setChunks((prev) => prev.filter((c) => c.id !== chunkId));
    } catch {
      alert("삭제 실패");
    } finally {
      setDeletingId(null);
    }
  }

  const doc = docs.find((d) => d.source === selectedSource);

  return (
    <div style={{ display: "flex", gap: 24, height: "calc(100vh - 72px)" }}>
      {/* 문서 목록 */}
      <div
        style={{
          width: 220,
          flexShrink: 0,
          overflowY: "auto",
          borderRight: "1px solid var(--border)",
          paddingRight: 16,
        }}
      >
        <h3 style={{ marginTop: 0, marginBottom: 12, fontSize: "0.95rem" }}>
          문서 목록 ({docs.length})
        </h3>
        {docs.length === 0 && (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            업로드된 문서 없음
          </p>
        )}
        {docs.map((doc) => (
          <div
            key={doc.source}
            onClick={() => selectDoc(doc.source)}
            style={{
              padding: "8px 10px",
              borderRadius: 8,
              cursor: "pointer",
              background:
                selectedSource === doc.source
                  ? "var(--accent)"
                  : "transparent",
              color:
                selectedSource === doc.source ? "white" : "var(--muted)",
              fontSize: "0.85rem",
              marginBottom: 4,
              wordBreak: "break-all",
              lineHeight: 1.4,
            }}
          >
            <div
              style={{
                display: "inline-block",
                fontSize: "0.7rem",
                background:
                  selectedSource === doc.source
                    ? "rgba(255,255,255,0.25)"
                    : "var(--border)",
                borderRadius: 3,
                padding: "1px 5px",
                marginBottom: 4,
              }}
            >
              {doc.doc_type}
            </div>
            <div>{doc.source}</div>
          </div>
        ))}
      </div>

      {/* 청크 뷰어 */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {!selectedSource ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "var(--muted)",
            }}
          >
            좌측에서 문서를 선택하세요
          </div>
        ) : loadingChunks ? (
          <p className="muted">청크 로딩 중...</p>
        ) : (
          <>
            {/* 헤더 */}
            <div
              className="row"
              style={{ marginBottom: 12, flexWrap: "wrap", gap: 8 }}
            >
              <h3 style={{ margin: 0, wordBreak: "break-all" }}>
                {selectedSource}
              </h3>
              {doc && (
                <span className="badge" style={{ background: "#4f7cff" }}>
                  {doc.doc_type}
                </span>
              )}
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                {chunks.length}개 청크
              </span>

              {/* 탭 스위처 */}
              <div
                style={{
                  marginLeft: "auto",
                  display: "flex",
                  gap: 3,
                  background: "var(--panel)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: 3,
                }}
              >
                {(["chunks", "graph"] as ViewMode[]).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setViewMode(mode)}
                    style={{
                      padding: "5px 14px",
                      borderRadius: 6,
                      fontSize: "0.8rem",
                      background: viewMode === mode ? "var(--accent)" : "transparent",
                      color: viewMode === mode ? "white" : "var(--muted)",
                      border: "none",
                      cursor: "pointer",
                      fontWeight: viewMode === mode ? 600 : 400,
                      transition: "background 0.15s, color 0.15s",
                    }}
                  >
                    {mode === "chunks" ? "청크 목록" : "그래프 뷰"}
                  </button>
                ))}
              </div>
            </div>

            {/* 그래프 뷰 */}
            {viewMode === "graph" && (
              <NeovisGraph source={selectedSource!} />
            )}

            {/* 청크 목록 뷰 */}
            {viewMode === "chunks" && (
            <>
            {/* 중요도 범례 */}
            <div
              style={{
                display: "flex",
                gap: 12,
                flexWrap: "wrap",
                marginBottom: 16,
                padding: "10px 14px",
                background: "var(--panel)",
                border: "1px solid var(--border)",
                borderRadius: 10,
              }}
            >
              {Object.entries(IMPORTANCE_DESC).map(([level, desc]) => (
                <div key={level} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: 3,
                      background: IMPORTANCE_COLOR[level],
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
                    <b style={{ color: "var(--text)" }}>{level}</b> — {desc.split(" — ")[1]}
                  </span>
                </div>
              ))}
            </div>

            {chunks.map((chunk) => (
              <div
                key={chunk.id}
                className="card"
                style={{
                  marginBottom: 10,
                  borderColor: editingId === chunk.id
                    ? "var(--accent)"
                    : IMPORTANCE_COLOR[chunk.importance] ?? "var(--border)",
                  borderWidth: 1.5,
                  background: importanceBg(chunk.importance, chunk.color_intensity),
                }}
              >
                {/* 헤더 */}
                <div
                  className="row"
                  style={{ marginBottom: 8, flexWrap: "wrap", gap: 6 }}
                >
                  <span
                    className="badge"
                    style={{
                      background:
                        IMPORTANCE_COLOR[chunk.importance] ?? "#9aa1b1",
                    }}
                  >
                    {chunk.importance}
                  </span>
                  {chunk.user_adjusted && (
                    <span
                      className="badge"
                      style={{ background: "#ff7c4f" }}
                    >
                      수정됨
                    </span>
                  )}
                  <span className="muted" style={{ fontSize: "0.78rem" }}>
                    {chunk.chunker_used}
                  </span>
                  <span className="muted" style={{ fontSize: "0.78rem" }}>
                    score {chunk.importance_score.toFixed(3)}
                  </span>
                  {chunk.section && (
                    <span className="muted" style={{ fontSize: "0.78rem" }}>
                      § {chunk.section}
                    </span>
                  )}
                  <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                    {editingId === chunk.id ? (
                      <>
                        <button
                          style={{ padding: "4px 10px", fontSize: "0.8rem" }}
                          onClick={() => saveEdit(chunk)}
                          disabled={savingId === chunk.id}
                        >
                          {savingId === chunk.id ? "저장 중..." : "저장"}
                        </button>
                        <button
                          className="secondary"
                          style={{ padding: "4px 10px", fontSize: "0.8rem" }}
                          onClick={() => setEditingId(null)}
                        >
                          취소
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          className="secondary"
                          style={{ padding: "4px 10px", fontSize: "0.8rem" }}
                          onClick={() => startEdit(chunk)}
                        >
                          편집
                        </button>
                        <button
                          className="secondary"
                          style={{
                            padding: "4px 10px",
                            fontSize: "0.8rem",
                            color: "#ff4f4f",
                            borderColor: "#ff4f4f",
                          }}
                          onClick={() => handleDelete(chunk.id)}
                          disabled={deletingId === chunk.id}
                        >
                          {deletingId === chunk.id ? "..." : "삭제"}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* 텍스트 / 편집 */}
                {editingId === chunk.id ? (
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    rows={6}
                    style={{ fontSize: "0.875rem", lineHeight: 1.6 }}
                  />
                ) : (
                  <p
                    style={{
                      margin: 0,
                      fontSize: "0.875rem",
                      lineHeight: 1.65,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {chunk.text}
                  </p>
                )}
              </div>
            ))}
            </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
