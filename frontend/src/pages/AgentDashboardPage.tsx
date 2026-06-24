import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listRegistry, getAgentDetail } from "../api/client";
import type { AgentRecord } from "../types";

const MODE_COLOR: Record<string, string> = {
  solo: "#3b82f6",
  dual: "#a855f7",
  reuse: "#22c55e",
};

export default function AgentDashboardPage() {
  const [agents, setAgents] = useState<AgentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<AgentRecord | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    listRegistry()
      .then((r) => setAgents(r.agents))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const openDetail = async (agentId: string) => {
    try {
      const detail = await getAgentDetail(agentId);
      setSelected(detail);
    } catch {
      setError("상세 조회 실패");
    }
  };

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>에이전트 관리</h2>
        <button onClick={() => navigate("/agents/create")}>+ 새 에이전트 생성</button>
      </div>

      {loading && <p className="muted">불러오는 중…</p>}
      {error && <p style={{ color: "#ef4444" }}>{error}</p>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
        {agents.map((a) => (
          <div
            key={a.agent_id}
            className="card"
            style={{ cursor: "pointer" }}
            onClick={() => openDetail(a.agent_id)}
          >
            <div className="row" style={{ marginBottom: 8 }}>
              <span
                className="badge"
                style={{ background: MODE_COLOR[a.mode] ?? "#6b7280" }}
              >
                {a.mode}
              </span>
              <span className="muted" style={{ fontSize: "0.78rem" }}>v{a.version}</span>
            </div>
            <p style={{ fontWeight: 600, fontSize: "0.95rem", margin: "0 0 4px" }}>
              {a.agent_id}
            </p>
            <p className="muted" style={{ fontSize: "0.82rem", margin: 0 }}>
              {a.user_request?.slice(0, 80)}
            </p>
            {a.created_at && (
              <p className="muted" style={{ fontSize: "0.72rem", marginTop: 6 }}>
                {a.created_at}
              </p>
            )}
          </div>
        ))}
      </div>

      {agents.length === 0 && !loading && (
        <div className="card" style={{ textAlign: "center" }}>
          <p className="muted">등록된 에이전트가 없습니다.</p>
          <button onClick={() => navigate("/agents/create")}>에이전트 생성하기</button>
        </div>
      )}

      {selected && (
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
          onClick={() => setSelected(null)}
        >
          <div
            className="card"
            style={{ width: 640, maxHeight: "80vh", overflow: "auto" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
              <h3 style={{ margin: 0 }}>{selected.agent_id}</h3>
              <button className="secondary" onClick={() => setSelected(null)}>닫기</button>
            </div>
            <div className="row" style={{ marginBottom: 12, gap: 8 }}>
              <span className="badge" style={{ background: MODE_COLOR[selected.mode] ?? "#6b7280" }}>
                {selected.mode}
              </span>
              <span className="muted">v{selected.version}</span>
            </div>

            <Section title="요구사항" content={selected.user_request} />
            <Section title="시스템 프롬프트" content={selected.system_prompt} />
            <Section title="에이전트 스펙" content={selected.agent_spec} />
            <Section title="MCP 도구" content={selected.mcp_tools} />
            <Section title="프로젝트 파일" content={selected.project_files} />
            <Section title="테스트 결과" content={selected.test_result} />
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ title, content }: { title: string; content?: unknown }) {
  if (!content) return null;
  const text = typeof content === "string" ? content : JSON.stringify(content, null, 2);
  return (
    <div style={{ marginBottom: 12 }}>
      <p style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 4 }}>{title}</p>
      <pre className="card" style={{ fontSize: "0.78rem", margin: 0 }}>
        {text}
      </pre>
    </div>
  );
}
