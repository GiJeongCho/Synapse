import { useEffect, useState } from "react";
import {
  listGeneratedTools,
  getToolDetail,
  executeTool,
} from "../api/client";
import type { GeneratedTool, ToolExecuteResult } from "../types";

export default function ToolsPage() {
  const [tools, setTools] = useState<GeneratedTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<GeneratedTool | null>(null);

  const [execFunc, setExecFunc] = useState("");
  const [execArgs, setExecArgs] = useState("{}");
  const [execResult, setExecResult] = useState<ToolExecuteResult | null>(null);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    listGeneratedTools()
      .then((r) => setTools(r.tools))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const openDetail = async (toolId: string) => {
    try {
      const detail = await getToolDetail(toolId);
      setSelected(detail);
      setExecFunc(detail.functions?.[0] ?? "");
      setExecArgs("{}");
      setExecResult(null);
    } catch {
      setError("도구 상세 조회 실패");
    }
  };

  const handleExecute = async () => {
    if (!selected) return;
    setExecuting(true);
    setExecResult(null);
    try {
      let parsedArgs: Record<string, unknown> = {};
      try {
        parsedArgs = JSON.parse(execArgs);
      } catch {
        setExecResult({ status: "error", error: "인자 JSON 파싱 실패" });
        setExecuting(false);
        return;
      }
      const result = await executeTool(selected.tool_id, execFunc, parsedArgs);
      setExecResult(result);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setExecResult({ status: "error", error: msg });
    } finally {
      setExecuting(false);
    }
  };

  const groupedByAgent: Record<string, GeneratedTool[]> = {};
  for (const tool of tools) {
    const agentId = tool.agent_id ?? "unknown";
    if (!groupedByAgent[agentId]) groupedByAgent[agentId] = [];
    groupedByAgent[agentId].push(tool);
  }

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>MCP 도구 관리</h2>
      {loading && <p className="muted">불러오는 중…</p>}
      {error && <p style={{ color: "#ef4444" }}>{error}</p>}

      {Object.entries(groupedByAgent).map(([agentId, agentTools]) => (
        <div key={agentId} style={{ marginBottom: 24 }}>
          <h4 style={{ color: "#a78bfa", marginBottom: 8 }}>
            Agent: {agentId}
          </h4>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
              gap: 10,
            }}
          >
            {agentTools.map((t) => (
              <div
                key={t.tool_id}
                className="card"
                style={{ cursor: "pointer" }}
                onClick={() => openDetail(t.tool_id)}
              >
                <p style={{ fontWeight: 600, fontSize: "0.92rem", margin: "0 0 4px" }}>
                  {t.name ?? t.tool_id}
                </p>
                <p className="muted" style={{ fontSize: "0.8rem", margin: 0 }}>
                  {t.description?.slice(0, 100) ?? "설명 없음"}
                </p>
                {t.functions && (
                  <div style={{ marginTop: 6 }}>
                    {t.functions.map((fn) => (
                      <span
                        key={fn}
                        className="badge"
                        style={{ background: "#1d4ed8", marginRight: 4, fontSize: "0.7rem" }}
                      >
                        {fn}()
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {tools.length === 0 && !loading && (
        <div className="card" style={{ textAlign: "center" }}>
          <p className="muted">생성된 MCP 도구가 없습니다.</p>
          <p className="muted" style={{ fontSize: "0.8rem" }}>
            에이전트를 생성하면 도구가 자동으로 만들어집니다.
          </p>
        </div>
      )}

      {/* 도구 상세 + 실행 모달 */}
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
            style={{ width: 720, maxHeight: "85vh", overflow: "auto" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              className="row"
              style={{ justifyContent: "space-between", marginBottom: 12 }}
            >
              <h3 style={{ margin: 0 }}>{selected.name ?? selected.tool_id}</h3>
              <button className="secondary" onClick={() => setSelected(null)}>
                닫기
              </button>
            </div>

            <p className="muted" style={{ fontSize: "0.85rem", marginBottom: 8 }}>
              {selected.description}
            </p>

            {selected.code && (
              <div style={{ marginBottom: 16 }}>
                <p style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 4 }}>
                  도구 코드
                </p>
                <pre
                  className="card"
                  style={{
                    fontSize: "0.75rem",
                    margin: 0,
                    maxHeight: 300,
                    overflow: "auto",
                    background: "#0d1117",
                  }}
                >
                  {selected.code}
                </pre>
              </div>
            )}

            <div
              style={{
                borderTop: "1px solid #2a2f40",
                paddingTop: 12,
                marginBottom: 12,
              }}
            >
              <p style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 8 }}>
                도구 실행
              </p>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <select
                  value={execFunc}
                  onChange={(e) => setExecFunc(e.target.value)}
                  style={{
                    flex: 1,
                    padding: "6px 10px",
                    background: "#1a1e2c",
                    border: "1px solid #3a3f52",
                    borderRadius: 6,
                    color: "#e0e3eb",
                  }}
                >
                  {(selected.functions ?? []).map((fn) => (
                    <option key={fn} value={fn}>
                      {fn}()
                    </option>
                  ))}
                </select>
                <button onClick={handleExecute} disabled={executing}>
                  {executing ? "실행 중…" : "실행"}
                </button>
              </div>
              <textarea
                value={execArgs}
                onChange={(e) => setExecArgs(e.target.value)}
                placeholder='{"key": "value"}'
                rows={3}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  background: "#0d1117",
                  border: "1px solid #3a3f52",
                  borderRadius: 6,
                  color: "#e0e3eb",
                  fontFamily: "monospace",
                  fontSize: "0.8rem",
                  resize: "vertical",
                }}
              />
            </div>

            {execResult && (
              <div style={{ marginTop: 8 }}>
                <p
                  style={{
                    fontWeight: 600,
                    fontSize: "0.85rem",
                    marginBottom: 4,
                    color: execResult.status === "success" ? "#22c55e" : "#ef4444",
                  }}
                >
                  {execResult.status === "success" ? "실행 성공" : "실행 실패"}
                </p>
                <pre
                  className="card"
                  style={{
                    fontSize: "0.75rem",
                    margin: 0,
                    maxHeight: 200,
                    overflow: "auto",
                    background: "#0d1117",
                  }}
                >
                  {JSON.stringify(execResult.result ?? execResult.error, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
