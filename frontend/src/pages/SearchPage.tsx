import { useState } from "react";
import { searchDocuments } from "../api/client";
import type { SearchResult } from "../types";

const DOC_TYPE_COLOR: Record<string, string> = {
  law: "#4f7cff",
  paper: "#7c5cff",
  news: "#ff7c4f",
  unknown: "#9aa1b1",
};

const IMPORTANCE_COLOR: Record<string, string> = {
  core: "#4f7cff",
  support: "#7c5cff",
  context: "#4faaff",
  noise: "#9aa1b1",
};

const DOC_TYPE_LABELS = ["전체", "law", "paper", "news"];
const IMPORTANCE_LABELS = ["전체", "core", "support", "context"];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(10);
  const [docTypeFilter, setDocTypeFilter] = useState("전체");
  const [importanceFilter, setImportanceFilter] = useState("전체");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function handleSearch(e?: React.FormEvent) {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setSearched(false);
    try {
      const res = await searchDocuments(
        query,
        topK,
        docTypeFilter === "전체" ? undefined : docTypeFilter,
        importanceFilter === "전체" ? undefined : importanceFilter,
      );
      setResults(res.results);
      setSearched(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "검색 실패");
    } finally {
      setLoading(false);
    }
  }

  function scoreBar(score: number) {
    const pct = Math.min(100, Math.round(score * 100));
    return (
      <div
        style={{
          height: 4,
          borderRadius: 2,
          background: "var(--border)",
          marginTop: 6,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: "var(--accent)",
            borderRadius: 2,
          }}
        />
      </div>
    );
  }

  return (
    <div>
      <h2>RAG 검색</h2>
      <p className="muted" style={{ marginTop: -8, marginBottom: 20 }}>
        하이브리드 검색 (벡터 + BM25 + 그래프) 으로 관련 청크를 찾습니다.
      </p>

      {/* 검색 폼 */}
      <form onSubmit={handleSearch} style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="검색어를 입력하세요 (예: 제3조 적용 범위)"
            style={{ flex: 1 }}
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? "검색 중..." : "검색"}
          </button>
        </div>

        {/* 필터 */}
        <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span className="muted" style={{ fontSize: "0.85rem" }}>문서 유형</span>
            {DOC_TYPE_LABELS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setDocTypeFilter(t)}
                style={{
                  padding: "3px 10px",
                  fontSize: "0.8rem",
                  background: docTypeFilter === t ? "var(--accent)" : "transparent",
                  border: `1px solid ${docTypeFilter === t ? "var(--accent)" : "var(--border)"}`,
                  color: docTypeFilter === t ? "white" : "var(--muted)",
                }}
              >
                {t}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span className="muted" style={{ fontSize: "0.85rem" }}>중요도</span>
            {IMPORTANCE_LABELS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setImportanceFilter(t)}
                style={{
                  padding: "3px 10px",
                  fontSize: "0.8rem",
                  background: importanceFilter === t ? "var(--accent)" : "transparent",
                  border: `1px solid ${importanceFilter === t ? "var(--accent)" : "var(--border)"}`,
                  color: importanceFilter === t ? "white" : "var(--muted)",
                }}
              >
                {t}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", gap: 6, alignItems: "center", marginLeft: "auto" }}>
            <span className="muted" style={{ fontSize: "0.85rem" }}>결과 수</span>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              style={{ width: "auto", padding: "4px 8px" }}
            >
              {[5, 10, 20].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>
      </form>

      {/* 에러 */}
      {error && (
        <div className="card" style={{ borderColor: "#ff4f4f", marginBottom: 16 }}>
          <p style={{ color: "#ff4f4f", margin: 0 }}>❌ {error}</p>
        </div>
      )}

      {/* 결과 */}
      {searched && (
        <div>
          <p className="muted" style={{ marginBottom: 12, fontSize: "0.88rem" }}>
            {results.length > 0
              ? `"${query}" — ${results.length}개 결과`
              : `"${query}"에 대한 결과가 없습니다.`}
          </p>

          {results.map((r, i) => {
            const isExpanded = expandedId === r.id;
            const preview = r.text.length > 200 ? r.text.slice(0, 200) + "…" : r.text;

            return (
              <div
                key={r.id}
                className="card"
                style={{ marginBottom: 10, cursor: "pointer" }}
                onClick={() => setExpandedId(isExpanded ? null : r.id)}
              >
                {/* 상단 메타 */}
                <div className="row" style={{ marginBottom: 8, flexWrap: "wrap", gap: 6 }}>
                  <span
                    style={{
                      color: "var(--muted)",
                      fontSize: "0.78rem",
                      minWidth: 20,
                    }}
                  >
                    #{i + 1}
                  </span>
                  <span
                    className="badge"
                    style={{ background: DOC_TYPE_COLOR[r.doc_type] ?? "#9aa1b1" }}
                  >
                    {r.doc_type}
                  </span>
                  <span
                    className="badge"
                    style={{ background: IMPORTANCE_COLOR[r.importance] ?? "#9aa1b1" }}
                  >
                    {r.importance}
                  </span>
                  <span
                    className="muted"
                    style={{ fontSize: "0.8rem", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                  >
                    {r.source}
                  </span>
                  <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--accent)" }}>
                    {(r.final_score ?? r.score ?? 0).toFixed(3)}
                  </span>
                </div>

                {/* 점수 바 */}
                {scoreBar(r.final_score ?? r.score ?? 0)}

                {/* 텍스트 */}
                <p
                  style={{
                    margin: "10px 0 0",
                    fontSize: "0.88rem",
                    lineHeight: 1.65,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    color: "var(--text)",
                  }}
                >
                  {isExpanded ? r.text : preview}
                </p>

                {r.text.length > 200 && (
                  <p
                    style={{
                      margin: "6px 0 0",
                      fontSize: "0.8rem",
                      color: "var(--accent)",
                    }}
                  >
                    {isExpanded ? "접기 ▲" : "더 보기 ▼"}
                  </p>
                )}

                {/* 상세 점수 (펼침 시) */}
                {isExpanded && (
                  <div
                    style={{
                      marginTop: 10,
                      padding: "8px 12px",
                      background: "rgba(0,0,0,0.2)",
                      borderRadius: 6,
                      fontSize: "0.78rem",
                      color: "var(--muted)",
                      display: "flex",
                      gap: 16,
                      flexWrap: "wrap",
                    }}
                  >
                    <span>vector score: <b style={{ color: "var(--text)" }}>{(r.score ?? 0).toFixed(4)}</b></span>
                    <span>rrf score: <b style={{ color: "var(--text)" }}>{(r.rrf_score ?? 0).toFixed(4)}</b></span>
                    <span>importance: <b style={{ color: "var(--text)" }}>{(r.importance_score ?? 0).toFixed(3)}</b></span>
                    <span>chunk id: <b style={{ color: "var(--text)" }}>{r.id}</b></span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!searched && !loading && (
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <p style={{ fontSize: "1.5rem", margin: "0 0 8px" }}>🔍</p>
          <p className="muted" style={{ margin: 0 }}>
            검색어를 입력하고 Enter 또는 검색 버튼을 누르세요
          </p>
        </div>
      )}
    </div>
  );
}
