import { useEffect, useRef, useState } from "react";

const NEO4J_URI      = import.meta.env.VITE_NEO4J_URI      ?? "bolt://localhost:7687";
const NEO4J_USER     = import.meta.env.VITE_NEO4J_USER     ?? "neo4j";
const NEO4J_PASSWORD = import.meta.env.VITE_NEO4J_PASSWORD ?? "synapse1234";

const CONTAINER_ID = "neovis-doc-graph";

const NODE_LEGEND = [
  { label: "Document", color: "#06b6d4", desc: "문서" },
  { label: "Article",  color: "#a855f7", desc: "조문" },
  { label: "Chunk",    color: "#4f7cff", desc: "청크" },
];

const REL_LEGEND = [
  { label: "HAS_CHUNK",    color: "#4f7cff", dashed: false },
  { label: "HAS_ARTICLE",  color: "#a855f7", dashed: false },
  { label: "NEXT_CHUNK",   color: "#4b5563", dashed: true  },
  { label: "NEXT_ARTICLE", color: "#7e22ce", dashed: true  },
];

function escapeCypher(s: string): string {
  return s.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

interface Props {
  source: string;
}

export default function NeovisGraph({ source }: Props) {
  const [status, setStatus]   = useState<"loading" | "ready" | "error">("loading");
  const [errorMsg, setError]  = useState("");
  const vizRef = useRef<unknown>(null);

  useEffect(() => {
    if (!source) return;

    let cancelled = false;
    setStatus("loading");
    setError("");

    (async () => {
      try {
        // Dynamic import — avoids Vite/SSR resolution issues
        const mod = await import("neovis.js");
        const NeoVis = mod.default as any;

        if (cancelled) return;

        // Clean up previous vis-network instance
        if (vizRef.current) {
          try { (vizRef.current as any).clearNetwork?.(); } catch { /* ignore */ }
          vizRef.current = null;
        }

        const esc     = escapeCypher(source);
        const cypher  = `MATCH (n) WHERE n.source = "${esc}" OPTIONAL MATCH (n)-[r]->(m) WHERE m.source = "${esc}" RETURN n, r, m`;
        const dflt    = NeoVis.NEOVIS_DEFAULT_CONFIG;

        const viz = new NeoVis({
          containerId: CONTAINER_ID,
          neo4j: {
            serverUrl:      NEO4J_URI,
            serverUser:     NEO4J_USER,
            serverPassword: NEO4J_PASSWORD,
          },
          visConfig: {
            nodes: {
              shape: "dot",
              font: { size: 12, color: "#e2e8f0" },
              borderWidth: 2,
            },
            edges: {
              arrows: { to: { enabled: true, scaleFactor: 0.55 } },
              font:   { size: 9, color: "#6b7280", strokeWidth: 0, align: "middle" },
              smooth: { enabled: true, type: "continuous", roundness: 0.4 },
            },
            physics: {
              enabled: true,
              stabilization: { iterations: 200, updateInterval: 20 },
              barnesHut: {
                gravitationalConstant: -9000,
                centralGravity: 0.25,
                springConstant: 0.04,
                springLength: 130,
                damping: 0.12,
              },
            },
            interaction: {
              hover: true,
              navigationButtons: true,
              keyboard: false,
              tooltipDelay: 100,
            },
          },
          labels: {
            Document: {
              label: "source",
              [dflt]: {
                size: 42,
                color: {
                  background: "#0c4a6e",
                  border:     "#06b6d4",
                  highlight:  { background: "#0e7490", border: "#22d3ee" },
                  hover:      { background: "#075985", border: "#38bdf8" },
                },
                font:  { size: 14, color: "#bae6fd", face: "monospace" },
                title: "Document",
              },
            },
            Article: {
              label: "article_no",
              [dflt]: {
                size: 30,
                color: {
                  background: "#3b0764",
                  border:     "#a855f7",
                  highlight:  { background: "#581c87", border: "#c084fc" },
                  hover:      { background: "#4a1d96", border: "#d8b4fe" },
                },
                font:  { size: 12, color: "#ede9fe" },
                title: "Article",
              },
            },
            Chunk: {
              label: "section",
              [dflt]: {
                size: 18,
                color: {
                  background: "#1e3a8a",
                  border:     "#4f7cff",
                  highlight:  { background: "#1d4ed8", border: "#7fa0ff" },
                  hover:      { background: "#1e40af", border: "#93c5fd" },
                },
                font:  { size: 10, color: "#bfdbfe" },
                title: "Chunk",
              },
            },
          },
          relationships: {
            HAS_CHUNK: {
              label:  false,
              [dflt]: { color: { color: "#4f7cff", highlight: "#7fa0ff" }, width: 2 },
            },
            HAS_ARTICLE: {
              label:  false,
              [dflt]: { color: { color: "#a855f7", highlight: "#c084fc" }, width: 2 },
            },
            NEXT_CHUNK: {
              label:  false,
              [dflt]: { dashes: [5, 5], color: { color: "#374151", highlight: "#6b7280" }, width: 1 },
            },
            NEXT_ARTICLE: {
              label:  false,
              [dflt]: { dashes: [5, 5], color: { color: "#6b21a8", highlight: "#a855f7" }, width: 1 },
            },
          },
          initialCypher: cypher,
        } as any);

        viz.registerOnEvent("completed", () => {
          if (!cancelled) setStatus("ready");
        });

        viz.registerOnEvent("error", (e: unknown) => {
          if (!cancelled) {
            setStatus("error");
            const m = typeof e === "string" ? e : (e as any)?.message ?? "Neo4j 연결 오류";
            setError(m);
          }
        });

        viz.render();
        vizRef.current = viz;
      } catch (e: unknown) {
        if (!cancelled) {
          setStatus("error");
          setError((e as any)?.message ?? "Neovis 초기화 실패");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [source]);

  return (
    <div>
      {/* 범례 + 상태 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
          marginBottom: 12,
          padding: "9px 14px",
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 10,
        }}
      >
        {/* 노드 범례 */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {NODE_LEGEND.map((n) => (
            <div key={n.label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: n.color, flexShrink: 0 }} />
              <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
                <b style={{ color: "var(--text)" }}>{n.label}</b>
              </span>
            </div>
          ))}
        </div>

        <div style={{ width: 1, height: 14, background: "var(--border)" }} />

        {/* 관계 범례 */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {REL_LEGEND.map((r) => (
            <div key={r.label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <svg width="22" height="8" style={{ flexShrink: 0 }}>
                <line
                  x1="0" y1="4" x2="22" y2="4"
                  stroke={r.color}
                  strokeWidth={r.dashed ? 1 : 2}
                  strokeDasharray={r.dashed ? "4,3" : undefined}
                />
              </svg>
              <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>{r.label}</span>
            </div>
          ))}
        </div>

        {/* 상태 표시 */}
        <div style={{ marginLeft: "auto", fontSize: "0.75rem" }}>
          {status === "loading" && <span style={{ color: "var(--muted)" }}>로딩 중...</span>}
          {status === "error"   && (
            <span style={{ color: "#f87171" }}>
              {errorMsg.includes("WebSocket") || errorMsg.includes("bolt")
                ? "Neo4j 연결 실패 — bolt://localhost:7687 확인"
                : errorMsg}
            </span>
          )}
        </div>
      </div>

      {/* Neovis 캔버스 */}
      <div
        id={CONTAINER_ID}
        style={{
          height: 600,
          background: "#0d1117",
          border: "1px solid var(--border)",
          borderRadius: 12,
          overflow: "hidden",
          position: "relative",
        }}
      />

      {/* 사용 팁 */}
      {status === "ready" && (
        <p style={{ margin: "8px 0 0", fontSize: "0.73rem", color: "var(--muted)", textAlign: "right" }}>
          드래그로 이동 · 스크롤로 줌 · 노드 클릭 시 속성 확인
        </p>
      )}
    </div>
  );
}
