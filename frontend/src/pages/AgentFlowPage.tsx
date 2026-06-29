import { useEffect, useState } from "react";
import DynamicFlow from "../components/flow/DynamicFlow";
import {
  listBuiltinWorkflows,
  getBuiltinWorkflowGraph,
  listRegistry,
  getAgentWorkflowGraph,
} from "../api/client";
import type { WorkflowGraph, WorkflowListItem, AgentRecord } from "../types";

import {
  pipelineNodes, pipelineEdges,
  supervisorNodes, supervisorEdges,
  researchNodes, researchEdges,
} from "../components/flow/flowConfig";

const STATIC_FALLBACKS: Record<string, WorkflowGraph> = {
  meta_agent_pipeline: {
    display_name: "Meta-Agent 파이프라인",
    category: "메타 에이전트",
    nodes: pipelineNodes as WorkflowGraph["nodes"],
    edges: pipelineEdges as WorkflowGraph["edges"],
  },
  dual_supervisor: {
    display_name: "Dual Supervisor",
    category: "메타 에이전트",
    nodes: supervisorNodes as WorkflowGraph["nodes"],
    edges: supervisorEdges as WorkflowGraph["edges"],
  },
  research_supervisor: {
    display_name: "Research Supervisor",
    category: "오케스트레이션",
    nodes: researchNodes as WorkflowGraph["nodes"],
    edges: researchEdges as WorkflowGraph["edges"],
  },
};

const CATEGORY_COLORS: Record<string, string> = {
  "워커 에이전트": "#3b82f6",
  "오케스트레이션": "#22c55e",
  "메타 에이전트": "#a855f7",
  "생성된 에이전트": "#f59e0b",
  기타: "#6b7280",
};

export default function AgentFlowPage() {
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [agents, setAgents] = useState<AgentRecord[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [selectedType, setSelectedType] = useState<"builtin" | "agent">("builtin");
  const [graph, setGraph] = useState<WorkflowGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadWorkflowList();
  }, []);

  async function loadWorkflowList() {
    try {
      const [wfs, reg] = await Promise.all([
        listBuiltinWorkflows().catch(() => [] as WorkflowListItem[]),
        listRegistry().catch(() => ({ agents: [] as AgentRecord[], total: 0 })),
      ]);
      setWorkflows(wfs);
      setAgents(reg.agents);

      if (wfs.length > 0) {
        selectWorkflow(wfs[0].name, "builtin");
      }
    } catch {
      setError("워크플로우 목록 로딩 실패");
    }
  }

  async function selectWorkflow(name: string, type: "builtin" | "agent") {
    setSelected(name);
    setSelectedType(type);
    setLoading(true);
    setError("");

    try {
      let data: WorkflowGraph;
      if (type === "builtin") {
        data = await getBuiltinWorkflowGraph(name);
      } else {
        data = await getAgentWorkflowGraph(name);
      }
      // 방어: nodes/edges 누락 시 빈 배열 보장 (렌더 크래시 방지)
      data = { ...data, nodes: data.nodes ?? [], edges: data.edges ?? [] };
      if (data.nodes.length === 0) {
        throw new Error("empty graph");
      }
      setGraph(data);
    } catch {
      const fallback = STATIC_FALLBACKS[name];
      if (fallback) {
        setGraph(fallback);
      } else if (type === "agent") {
        const agent = agents.find((a) => a.agent_id === name);
        setGraph({
          display_name: agent?.user_request?.slice(0, 40) ?? name,
          category: "생성된 에이전트",
          nodes: [
            { id: "agent", type: "flowCard", position: { x: 0, y: 0 }, data: { label: name.slice(0, 20), desc: agent?.user_request ?? "" } },
          ],
          edges: [],
        });
      } else {
        setError("그래프를 불러올 수 없습니다.");
        setGraph(null);
      }
    } finally {
      setLoading(false);
    }
  }

  const grouped = new Map<string, WorkflowListItem[]>();
  for (const wf of workflows) {
    const list = grouped.get(wf.category) ?? [];
    list.push(wf);
    grouped.set(wf.category, list);
  }

  return (
    <div>
      <h2>에이전트 흐름도</h2>
      <p className="muted" style={{ marginBottom: 20 }}>
        워크플로우를 선택하면 실제 LangGraph 구조가 시각화됩니다. 노드 클릭 시 설명이 표시됩니다.
      </p>

      <div style={{ display: "flex", gap: 16 }}>
        {/* 좌측: 워크플로우 목록 */}
        <div style={{ width: 220, flexShrink: 0 }}>
          {[...grouped.entries()].map(([category, items]) => (
            <div key={category} style={{ marginBottom: 16 }}>
              <p
                style={{
                  fontSize: "0.72rem",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  color: CATEGORY_COLORS[category] ?? "#6b7280",
                  marginBottom: 6,
                  letterSpacing: "0.05em",
                }}
              >
                {category}
              </p>
              {items.map((wf) => (
                <button
                  key={wf.name}
                  className={selected === wf.name && selectedType === "builtin" ? "" : "secondary"}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    fontSize: "0.82rem",
                    marginBottom: 4,
                    padding: "7px 10px",
                  }}
                  onClick={() => selectWorkflow(wf.name, "builtin")}
                >
                  {wf.display_name}
                </button>
              ))}
            </div>
          ))}

          {agents.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <p
                style={{
                  fontSize: "0.72rem",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  color: CATEGORY_COLORS["생성된 에이전트"],
                  marginBottom: 6,
                  letterSpacing: "0.05em",
                }}
              >
                생성된 에이전트
              </p>
              {agents.map((a) => (
                <button
                  key={a.agent_id}
                  className={selected === a.agent_id && selectedType === "agent" ? "" : "secondary"}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    fontSize: "0.82rem",
                    marginBottom: 4,
                    padding: "7px 10px",
                  }}
                  onClick={() => selectWorkflow(a.agent_id, "agent")}
                >
                  {a.agent_id.slice(0, 20)}
                </button>
              ))}
            </div>
          )}

          {workflows.length === 0 && (
            <p className="muted" style={{ fontSize: "0.8rem" }}>
              백엔드에 연결할 수 없어 정적 흐름도를 표시합니다.
            </p>
          )}
        </div>

        {/* 우측: 그래프 영역 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {graph && (
            <div style={{ marginBottom: 12 }}>
              <div className="row" style={{ gap: 8 }}>
                <h3 style={{ margin: 0 }}>{graph.display_name}</h3>
                <span
                  className="badge"
                  style={{ background: CATEGORY_COLORS[graph.category] ?? "#6b7280" }}
                >
                  {graph.category}
                </span>
              </div>
              <p className="muted" style={{ fontSize: "0.78rem", margin: "4px 0 0" }}>
                노드 {graph.nodes.length}개 · 엣지 {graph.edges.length}개
              </p>
            </div>
          )}

          {loading && <p className="muted">불러오는 중…</p>}
          {error && <p style={{ color: "#ef4444" }}>{error}</p>}

          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            {graph ? (
              <DynamicFlow nodes={graph.nodes} edges={graph.edges} height={480} />
            ) : (
              !loading && (
                <div style={{ height: 480, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <p className="muted">좌측에서 워크플로우를 선택하세요.</p>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
