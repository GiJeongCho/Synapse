import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  listRegistry,
  getAgentDetail,
  deleteAgent,
  checkAgentPrereqs,
  runAgent,
} from "../api/client";
import type { AgentRecord } from "../types";

const MODE_COLOR: Record<string, string> = {
  solo: "#3b82f6",
  dual: "#a855f7",
  reuse: "#22c55e",
};

interface PrereqCheck {
  capability: string;
  label: string;
  ok: boolean;
  hint: string;
}

interface RunResult {
  tool_id: string;
  function: string;
  result: Record<string, unknown>;
}

export default function AgentDashboardPage() {
  const [agents, setAgents] = useState<AgentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<AgentRecord | null>(null);
  const navigate = useNavigate();

  const [prereqs, setPrereqs] = useState<PrereqCheck[]>([]);
  const [prereqLoading, setPrereqLoading] = useState(false);
  const [toolCount, setToolCount] = useState(0);

  const [running, setRunning] = useState(false);
  const [runResults, setRunResults] = useState<RunResult[] | null>(null);
  const [runStatus, setRunStatus] = useState("");
  const [runMessage, setRunMessage] = useState("");

  useEffect(() => {
    listRegistry()
      .then((r) => setAgents(r.agents))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const openDetail = async (agentId: string) => {
    setRunResults(null);
    setRunStatus("");
    setRunMessage("");
    setPrereqs([]);
    try {
      const [detail, prereqData] = await Promise.all([
        getAgentDetail(agentId),
        checkAgentPrereqs(agentId).catch(() => null),
      ]);
      setSelected(detail);
      if (prereqData) {
        setPrereqs(prereqData.checks);
        setToolCount(prereqData.tool_count);
      }
    } catch {
      setError("상세 조회 실패");
    }
  };

  const handleDelete = async (agentId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`"${agentId}" 에이전트를 삭제하시겠습니까?\n연관된 MCP 도구도 함께 삭제됩니다.`)) return;
    try {
      await deleteAgent(agentId);
      setAgents((prev) => prev.filter((a) => a.agent_id !== agentId));
      if (selected?.agent_id === agentId) setSelected(null);
    } catch {
      setError("삭제 실패");
    }
  };

  const handleRun = async (agentId: string) => {
    setRunning(true);
    setRunResults(null);
    setRunStatus("");
    setRunMessage("");
    try {
      const res = await runAgent(agentId);
      setRunStatus(res.status);
      if (res.status === "blocked") {
        setRunMessage(res.message ?? "필수 설정이 누락되었습니다.");
        if (res.failed_checks) {
          setPrereqs((prev) =>
            prev.map((p) => {
              const failed = res.failed_checks!.find((f) => f.capability === p.capability);
              return failed ? { ...p, ok: false, hint: failed.hint } : p;
            }),
          );
        }
      } else {
        setRunResults(res.results);
        setRunMessage(res.status === "success" ? "모든 도구가 성공적으로 실행되었습니다." : "일부 도구 실행에 실패했습니다.");
      }
    } catch (e: unknown) {
      setRunStatus("error");
      setRunMessage(e instanceof Error ? e.message : "실행 실패");
    } finally {
      setRunning(false);
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
              <span className="badge" style={{ background: MODE_COLOR[a.mode] ?? "#6b7280" }}>
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
            <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
              {a.created_at && (
                <span className="muted" style={{ fontSize: "0.72rem" }}>
                  {a.created_at}
                </span>
              )}
              <div className="row" style={{ gap: 4 }}>
                <button
                  className="secondary"
                  style={{ fontSize: "0.72rem", padding: "2px 8px" }}
                  onClick={(e) => { e.stopPropagation(); openDetail(a.agent_id).then(() => handleRun(a.agent_id)); }}
                >
                  실행
                </button>
                <button
                  className="secondary"
                  style={{ fontSize: "0.72rem", padding: "2px 8px", color: "#ef4444", borderColor: "#ef4444" }}
                  onClick={(e) => handleDelete(a.agent_id, e)}
                >
                  삭제
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {agents.length === 0 && !loading && (
        <div className="card" style={{ textAlign: "center" }}>
          <p className="muted">등록된 에이전트가 없습니다.</p>
          <button onClick={() => navigate("/agents/create")}>에이전트 생성하기</button>
        </div>
      )}

      {/* 상세 모달 */}
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
            style={{ width: 700, maxHeight: "85vh", overflow: "auto" }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* 헤더 */}
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
              <h3 style={{ margin: 0 }}>{selected.agent_id}</h3>
              <div className="row" style={{ gap: 8 }}>
                <button
                  onClick={() => handleRun(selected.agent_id)}
                  disabled={running}
                  style={{
                    fontSize: "0.8rem",
                    padding: "4px 14px",
                    background: "#2563eb",
                    border: "none",
                    color: "#fff",
                    borderRadius: 6,
                    cursor: running ? "wait" : "pointer",
                  }}
                >
                  {running ? "실행 중…" : "실행"}
                </button>
                <button
                  style={{
                    fontSize: "0.8rem",
                    padding: "4px 12px",
                    background: "#dc2626",
                    border: "none",
                    color: "#fff",
                    borderRadius: 6,
                    cursor: "pointer",
                  }}
                  onClick={(e) => handleDelete(selected.agent_id, e)}
                >
                  삭제
                </button>
                <button className="secondary" onClick={() => setSelected(null)}>닫기</button>
              </div>
            </div>

            <div className="row" style={{ marginBottom: 12, gap: 8 }}>
              <span className="badge" style={{ background: MODE_COLOR[selected.mode] ?? "#6b7280" }}>
                {selected.mode}
              </span>
              <span className="muted">v{selected.version}</span>
              <span className="muted" style={{ fontSize: "0.75rem" }}>
                도구 {toolCount}개
              </span>
            </div>

            {/* 사전 요구사항 체크 */}
            {prereqs.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <p style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 6 }}>
                  실행 요구사항
                </p>
                {prereqs.map((c) => (
                  <div
                    key={c.capability}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 8,
                      marginBottom: 6,
                      padding: "6px 10px",
                      borderRadius: 6,
                      background: c.ok ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
                      border: `1px solid ${c.ok ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}`,
                    }}
                  >
                    <span style={{ fontSize: "1rem", lineHeight: 1 }}>
                      {c.ok ? "✓" : "✗"}
                    </span>
                    <div>
                      <p style={{
                        margin: 0,
                        fontSize: "0.82rem",
                        fontWeight: 600,
                        color: c.ok ? "#22c55e" : "#ef4444",
                      }}>
                        {c.label}
                      </p>
                      {!c.ok && c.hint && (
                        <p style={{ margin: "2px 0 0", fontSize: "0.75rem", color: "#f59e0b" }}>
                          {c.hint}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* 실행 결과 */}
            {runStatus && (
              <div style={{
                marginBottom: 16,
                padding: "10px 14px",
                borderRadius: 8,
                background: runStatus === "success"
                  ? "rgba(34,197,94,0.1)"
                  : runStatus === "blocked"
                    ? "rgba(245,158,11,0.1)"
                    : "rgba(239,68,68,0.1)",
                border: `1px solid ${
                  runStatus === "success" ? "rgba(34,197,94,0.3)"
                    : runStatus === "blocked" ? "rgba(245,158,11,0.3)"
                      : "rgba(239,68,68,0.3)"
                }`,
              }}>
                <p style={{
                  fontWeight: 700,
                  fontSize: "0.88rem",
                  margin: "0 0 4px",
                  color: runStatus === "success" ? "#22c55e"
                    : runStatus === "blocked" ? "#f59e0b" : "#ef4444",
                }}>
                  {runStatus === "success" ? "실행 완료" : runStatus === "blocked" ? "실행 차단" : "실행 실패"}
                </p>
                <p style={{ fontSize: "0.8rem", margin: 0, color: "#c8cdd8" }}>
                  {runMessage}
                </p>
              </div>
            )}

            {runResults && runResults.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <p style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 6 }}>
                  실행 결과
                </p>
                {runResults.map((r, i) => (
                  <div key={i} className="card" style={{ padding: "8px 12px", marginBottom: 6 }}>
                    <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>
                        {r.tool_id.split("__").pop()}/{r.function}
                      </span>
                      <span
                        className="badge"
                        style={{
                          background: r.result?.status === "success" ? "#22c55e" : "#ef4444",
                          fontSize: "0.68rem",
                        }}
                      >
                        {(r.result?.status as string) ?? "unknown"}
                      </span>
                    </div>
                    <pre style={{
                      fontSize: "0.72rem",
                      margin: 0,
                      maxHeight: 120,
                      overflow: "auto",
                      color: "#9ca3af",
                    }}>
                      {JSON.stringify(r.result?.result ?? r.result?.error ?? r.result?.stderr, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}

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
      <pre className="card" style={{ fontSize: "0.78rem", margin: 0, maxHeight: 200, overflow: "auto" }}>
        {text}
      </pre>
    </div>
  );
}
