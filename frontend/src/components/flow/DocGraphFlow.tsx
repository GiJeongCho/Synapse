import { memo, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import dagre from "@dagrejs/dagre";
import { getDocumentGraph, type GraphNodeData, type DocumentGraphResponse } from "../../api/client";

// ── 노드 색상 팔레트 ────────────────────────────────────────────────────────
const NODE_PALETTE: Record<string, { border: string; bg: string; text: string; label: string }> = {
  Document: { border: "#06b6d4", bg: "#0a2733", text: "#67e8f9", label: "DOCUMENT" },
  Article:  { border: "#a855f7", bg: "#231040", text: "#d8b4fe", label: "ARTICLE"  },
  Chunk:    { border: "#4f7cff", bg: "#131e3a", text: "#93c5fd", label: "CHUNK"    },
};

const EDGE_COLORS: Record<string, string> = {
  HAS_CHUNK:    "#4f7cff",
  HAS_ARTICLE:  "#a855f7",
  NEXT_CHUNK:   "#374151",
  NEXT_ARTICLE: "#7e22ce",
};

// ── 커스텀 노드 ─────────────────────────────────────────────────────────────
interface GraphNodeContent {
  nodeType: string;
  label: string;
  sub: string;
}

const GraphNode = memo(({ data }: NodeProps<GraphNodeContent>) => {
  const c = NODE_PALETTE[data.nodeType] ?? NODE_PALETTE.Chunk;
  const isDoc = data.nodeType === "Document";

  return (
    <div
      style={{
        background: c.bg,
        border: `${isDoc ? 2 : 1.5}px solid ${c.border}`,
        borderRadius: 10,
        padding: isDoc ? "10px 16px" : "7px 12px",
        minWidth: isDoc ? 140 : 110,
        maxWidth: 180,
        boxShadow: `0 0 ${isDoc ? 16 : 8}px ${c.border}50`,
        textAlign: "center",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: c.border, width: 7, height: 7 }}
      />

      {/* 타입 배지 */}
      <div
        style={{
          fontSize: "0.58rem",
          fontWeight: 700,
          letterSpacing: "0.08em",
          color: c.border,
          marginBottom: 4,
        }}
      >
        {c.label}
      </div>

      {/* 메인 라벨 */}
      <div
        style={{
          fontSize: isDoc ? "0.82rem" : "0.72rem",
          fontWeight: isDoc ? 700 : 500,
          color: c.text,
          wordBreak: "break-all",
          lineHeight: 1.35,
        }}
      >
        {data.label}
      </div>

      {/* 서브 라벨 (Article의 article_no 등) */}
      {data.sub && data.sub !== data.label && (
        <div style={{ fontSize: "0.62rem", color: "#6b7280", marginTop: 3 }}>
          {data.sub}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: c.border, width: 7, height: 7 }}
      />
    </div>
  );
});

const nodeTypes = { graphNode: GraphNode };

// ── Dagre 레이아웃 ──────────────────────────────────────────────────────────
const NODE_W = 160;
const NODE_H = 72;

function applyDagre(nodes: Node[], edges: Edge[]): Node[] {
  if (!nodes.length) return nodes;
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "TB", ranksep: 90, nodesep: 55 });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => {
    try { g.setEdge(e.source, e.target); } catch { /* ignore */ }
  });
  dagre.layout(g);
  return nodes.map((n) => {
    const pos = g.node(n.id);
    if (!pos) return n;
    return { ...n, position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 } };
  });
}

// ── 메인 컴포넌트 ────────────────────────────────────────────────────────────
interface DocGraphFlowProps {
  source: string;
}

export default function DocGraphFlow({ source }: DocGraphFlowProps) {
  const [data, setData] = useState<DocumentGraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showNextChunk, setShowNextChunk] = useState(false);
  const [showNextArticle, setShowNextArticle] = useState(false);

  useEffect(() => {
    if (!source) return;
    setLoading(true);
    setError(null);
    setData(null);
    getDocumentGraph(source)
      .then(setData)
      .catch((e) => setError(e?.message ?? "그래프 로드 실패"))
      .finally(() => setLoading(false));
  }, [source]);

  const { nodes, edges } = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };

    // 엣지 필터
    const filteredEdges = data.edges.filter((e) => {
      if (!showNextChunk && e.rel_type === "NEXT_CHUNK") return false;
      if (!showNextArticle && e.rel_type === "NEXT_ARTICLE") return false;
      return true;
    });

    const nodeIds = new Set(data.nodes.map((n: GraphNodeData) => n.id));
    const rfEdges: Edge[] = filteredEdges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.rel_type,
        type: "smoothstep",
        animated: e.rel_type === "HAS_CHUNK" || e.rel_type === "HAS_ARTICLE",
        style: {
          stroke: EDGE_COLORS[e.rel_type] ?? "#5a6278",
          strokeWidth: e.rel_type.startsWith("NEXT") ? 1 : 2,
          strokeDasharray: e.rel_type.startsWith("NEXT") ? "5,4" : undefined,
        },
        labelStyle: { fill: "#9aa1b1", fontSize: 9 },
        labelBgStyle: { fill: "#12141e", stroke: "#3a3f52", strokeWidth: 1 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 3,
      }));

    const rfNodes: Node[] = data.nodes.map((n: GraphNodeData) => ({
      id: n.id,
      type: "graphNode",
      position: { x: 0, y: 0 },
      data: { nodeType: n.node_type, label: n.label, sub: n.sub },
    }));

    const layouted = applyDagre(rfNodes, rfEdges);
    return { nodes: layouted, edges: rfEdges };
  }, [data, showNextChunk, showNextArticle]);

  // ── 통계 ──
  const stats = useMemo(() => {
    if (!data) return null;
    const count = (type: string) => data.nodes.filter((n: GraphNodeData) => n.node_type === type).length;
    const edgeCount = (rel: string) => data.edges.filter((e) => e.rel_type === rel).length;
    return {
      document: count("Document"),
      article: count("Article"),
      chunk: count("Chunk"),
      hasChunk: edgeCount("HAS_CHUNK"),
      hasArticle: edgeCount("HAS_ARTICLE"),
      nextChunk: edgeCount("NEXT_CHUNK"),
      nextArticle: edgeCount("NEXT_ARTICLE"),
    };
  }, [data]);

  // ── 렌더 ──
  if (loading) {
    return (
      <div style={centerStyle}>
        <div style={{ color: "#9aa1b1" }}>Neo4j 그래프 로딩 중...</div>
      </div>
    );
  }
  if (error) {
    return (
      <div style={centerStyle}>
        <div style={{ color: "#f87171" }}>{error}</div>
        <div style={{ color: "#6b7280", fontSize: "0.8rem", marginTop: 6 }}>
          Neo4j 연결을 확인하거나 문서를 다시 업로드해 보세요.
        </div>
      </div>
    );
  }
  if (!data || !nodes.length) {
    return (
      <div style={centerStyle}>
        <div style={{ color: "#9aa1b1" }}>그래프 데이터가 없습니다.</div>
        <div style={{ color: "#6b7280", fontSize: "0.8rem", marginTop: 6 }}>
          Neo4j에 해당 문서 정보가 없습니다. 문서를 다시 업로드해 보세요.
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* 통계 + 옵션 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 20,
          flexWrap: "wrap",
          marginBottom: 12,
          padding: "8px 14px",
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 10,
        }}
      >
        {/* 노드 통계 */}
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {(["Document", "Article", "Chunk"] as const).map((t) => {
            const cnt = t === "Document" ? stats!.document : t === "Article" ? stats!.article : stats!.chunk;
            const c = NODE_PALETTE[t];
            return (
              <div key={t} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div style={{ width: 9, height: 9, borderRadius: 2, background: c.border }} />
                <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
                  <b style={{ color: "var(--text)" }}>{cnt}</b> {t}
                </span>
              </div>
            );
          })}
        </div>

        <div style={{ width: 1, height: 16, background: "var(--border)" }} />

        {/* 엣지 통계 */}
        <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
          엣지 {data.edges.length}개
        </span>

        <div style={{ marginLeft: "auto", display: "flex", gap: 12 }}>
          {[
            { key: "nextChunk", label: "NEXT_CHUNK", value: showNextChunk, setter: setShowNextChunk },
            { key: "nextArticle", label: "NEXT_ARTICLE", value: showNextArticle, setter: setShowNextArticle },
          ].map(({ key, label, value, setter }) => (
            <label
              key={key}
              style={{ display: "flex", alignItems: "center", gap: 5, fontSize: "0.75rem", color: "var(--muted)", cursor: "pointer" }}
            >
              <input
                type="checkbox"
                checked={value}
                onChange={(e) => setter(e.target.checked)}
                style={{ cursor: "pointer" }}
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      {/* 그래프 캔버스 */}
      <div
        style={{
          height: 580,
          border: "1px solid var(--border)",
          borderRadius: 12,
          overflow: "hidden",
          background: "#0d1117",
        }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.35 }}
          proOptions={{ hideAttribution: true }}
          minZoom={0.15}
          maxZoom={3}
          defaultEdgeOptions={{ type: "smoothstep" }}
        >
          <Background color="#1e2233" gap={24} size={1} />
          <Controls
            style={{ background: "#1a1e2c", border: "1px solid #3a3f52", borderRadius: 8 }}
          />
          <MiniMap
            nodeColor={(n) => NODE_PALETTE[n.data?.nodeType]?.border ?? "#4f7cff"}
            maskColor="rgba(0,0,0,0.6)"
            style={{
              background: "#0d1117",
              border: "1px solid #3a3f52",
              borderRadius: 8,
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}

const centerStyle: React.CSSProperties = {
  height: 420,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  textAlign: "center",
};
