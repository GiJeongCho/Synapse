import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAgent } from "../api/client";
import type { CreateAgentResponse } from "../types";

export default function AgentCreatePage() {
  const [request, setRequest] = useState("");
  const [criticEnabled, setCriticEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CreateAgentResponse | null>(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async () => {
    if (request.trim().length < 5) {
      setError("요구사항을 5자 이상 입력하세요.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await createAgent({
        user_request: request,
        critic_enabled: criticEnabled,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "생성 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>에이전트 생성</h2>

      <div className="card">
        <label style={{ display: "block", marginBottom: 8, fontWeight: 600 }}>
          요구사항
        </label>
        <textarea
          rows={4}
          placeholder="생성할 에이전트의 목적과 기능을 설명하세요…"
          value={request}
          onChange={(e) => setRequest(e.target.value)}
        />

        <div className="row" style={{ marginTop: 16, justifyContent: "space-between" }}>
          <label className="row" style={{ gap: 8, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={criticEnabled}
              onChange={(e) => setCriticEnabled(e.target.checked)}
              style={{ width: 16, height: 16 }}
            />
            <span>Critic 모드 (Dual Supervisor)</span>
          </label>

          <button onClick={handleSubmit} disabled={loading}>
            {loading ? "생성 중…" : "에이전트 생성"}
          </button>
        </div>

        {error && <p style={{ color: "#ef4444", marginTop: 8 }}>{error}</p>}
      </div>

      {loading && (
        <div className="card" style={{ textAlign: "center" }}>
          <p className="muted">파이프라인 실행 중… 다소 시간이 걸릴 수 있습니다.</p>
          <div className="spinner" />
        </div>
      )}

      {result && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>생성 완료</h3>
          <div className="row" style={{ gap: 12, marginBottom: 12 }}>
            <span
              className="badge"
              style={{
                background:
                  result.mode === "dual"
                    ? "#a855f7"
                    : result.mode === "reuse"
                      ? "#22c55e"
                      : "#3b82f6",
              }}
            >
              {result.mode}
            </span>
            {result.registry_hit && (
              <span className="muted" style={{ fontSize: "0.8rem" }}>
                Registry에서 재사용됨
              </span>
            )}
          </div>
          <p>
            <strong>Agent ID:</strong> {result.agent_id}
          </p>
          <pre style={{ fontSize: "0.78rem" }}>
            {JSON.stringify(result.result, null, 2)}
          </pre>
          <div className="row" style={{ gap: 8, marginTop: 12 }}>
            <button onClick={() => navigate("/agents")}>목록으로</button>
            <button className="secondary" onClick={() => navigate("/agents/flow")}>
              흐름도 보기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
