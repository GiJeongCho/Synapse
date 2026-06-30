import { useEffect, useState } from "react";
import {
  listSchedules,
  registerSchedule,
  removeSchedule,
  getScheduleLogs,
  runScheduleNow,
  listRegistry,
} from "../api/client";

interface Schedule {
  schedule_id: string;
  agent_id: string;
  cron: string;
  description: string;
  enabled: boolean;
  next_run?: string | null;
  active?: boolean;
  created_at?: string;
}

interface LogEntry {
  schedule_id: string;
  agent_id: string;
  started_at: string;
  completed_at: string;
  results: { tool_id: string; function: string; result: Record<string, unknown> }[];
}

const CRON_PRESETS = [
  { label: "매일 09:10", value: "10 9 * * *" },
  { label: "매일 08:00", value: "0 8 * * *" },
  { label: "매일 18:00", value: "0 18 * * *" },
  { label: "매시 정각", value: "0 * * * *" },
  { label: "평일 09:00", value: "0 9 * * 1-5" },
  { label: "직접 입력", value: "" },
];

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [agents, setAgents] = useState<{ agent_id: string; user_request: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [formAgent, setFormAgent] = useState("");
  const [formCron, setFormCron] = useState("10 9 * * *");
  const [formCustomCron, setFormCustomCron] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logsFor, setLogsFor] = useState("");
  const [runningNow, setRunningNow] = useState<string | null>(null);

  useEffect(() => {
    refresh();
  }, []);

  async function refresh() {
    setLoading(true);
    try {
      const [sched, reg] = await Promise.all([
        listSchedules(),
        listRegistry().catch(() => ({ agents: [], total: 0 })),
      ]);
      setSchedules(sched.schedules);
      setAgents(reg.agents);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "로딩 실패");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister() {
    if (!formAgent) { setError("에이전트를 선택하세요."); return; }
    const cron = formCron || formCustomCron;
    if (!cron.trim()) { setError("cron 표현식을 입력하세요."); return; }

    setSubmitting(true);
    setError("");
    try {
      await registerSchedule(formAgent, cron, formDesc);
      setSuccess("스케줄 등록 완료!");
      setShowForm(false);
      setFormDesc("");
      await refresh();
      setTimeout(() => setSuccess(""), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "등록 실패");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(scheduleId: string) {
    if (!window.confirm("이 스케줄을 해제하시겠습니까?")) return;
    try {
      await removeSchedule(scheduleId);
      setSchedules((prev) => prev.filter((s) => s.schedule_id !== scheduleId));
    } catch {
      setError("해제 실패");
    }
  }

  async function handleRunNow(scheduleId: string) {
    setRunningNow(scheduleId);
    try {
      await runScheduleNow(scheduleId);
      setSuccess("즉시 실행 완료!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "실행 실패");
    } finally {
      setRunningNow(null);
    }
  }

  async function handleViewLogs(scheduleId: string) {
    if (logsFor === scheduleId) {
      setLogsFor("");
      setLogs([]);
      return;
    }
    try {
      const data = await getScheduleLogs(scheduleId);
      setLogs(data.logs);
      setLogsFor(scheduleId);
    } catch {
      setError("로그 조회 실패");
    }
  }

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>스케줄 관리</h2>
        <button onClick={() => setShowForm(!showForm)}>
          {showForm ? "취소" : "+ 스케줄 등록"}
        </button>
      </div>

      {error && <p style={{ color: "#ef4444", marginBottom: 12 }}>{error}</p>}
      {success && <p style={{ color: "#22c55e", marginBottom: 12 }}>{success}</p>}

      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h4 style={{ margin: "0 0 12px" }}>새 스케줄 등록</h4>

          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: "0.82rem", fontWeight: 600, display: "block", marginBottom: 4 }}>
              에이전트
            </label>
            <select
              value={formAgent}
              onChange={(e) => setFormAgent(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 10px",
                background: "#1a1e2c",
                border: "1px solid #3a3f52",
                borderRadius: 6,
                color: "#e0e3eb",
              }}
            >
              <option value="">선택하세요</option>
              {agents.map((a) => (
                <option key={a.agent_id} value={a.agent_id}>
                  {a.agent_id} — {a.user_request?.slice(0, 50)}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: "0.82rem", fontWeight: 600, display: "block", marginBottom: 4 }}>
              실행 주기
            </label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 6 }}>
              {CRON_PRESETS.map((p) => (
                <button
                  key={p.label}
                  className={formCron === p.value ? "" : "secondary"}
                  style={{ fontSize: "0.78rem", padding: "4px 10px" }}
                  onClick={() => setFormCron(p.value)}
                >
                  {p.label}
                </button>
              ))}
            </div>
            {formCron === "" && (
              <input
                type="text"
                placeholder="분 시 일 월 요일  (예: 30 8 * * 1-5)"
                value={formCustomCron}
                onChange={(e) => setFormCustomCron(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  background: "#0d1117",
                  border: "1px solid #3a3f52",
                  borderRadius: 6,
                  color: "#e0e3eb",
                  fontFamily: "monospace",
                }}
              />
            )}
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: "0.82rem", fontWeight: 600, display: "block", marginBottom: 4 }}>
              설명 (선택)
            </label>
            <input
              type="text"
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
              placeholder="예: 블룸버그 뉴스 요약 메일"
              style={{
                width: "100%",
                padding: "8px 10px",
                background: "#1a1e2c",
                border: "1px solid #3a3f52",
                borderRadius: 6,
                color: "#e0e3eb",
              }}
            />
          </div>

          <button onClick={handleRegister} disabled={submitting}>
            {submitting ? "등록 중…" : "스케줄 등록"}
          </button>
        </div>
      )}

      {loading && <p className="muted">불러오는 중…</p>}

      {schedules.length === 0 && !loading && (
        <div className="card" style={{ textAlign: "center" }}>
          <p className="muted">등록된 스케줄이 없습니다.</p>
          <p className="muted" style={{ fontSize: "0.8rem" }}>
            에이전트를 생성한 후 스케줄을 등록하면 자동으로 실행됩니다.
          </p>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {schedules.map((s) => (
          <div key={s.schedule_id}>
            <div className="card" style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: s.active ? "#22c55e" : "#6b7280",
                  flexShrink: 0,
                }}
              />
              <div style={{ flex: 1 }}>
                <p style={{ fontWeight: 600, fontSize: "0.9rem", margin: "0 0 2px" }}>
                  {s.description || s.agent_id}
                </p>
                <p className="muted" style={{ fontSize: "0.78rem", margin: 0 }}>
                  <code style={{ color: "#a78bfa" }}>{s.cron}</code>
                  {" · "}Agent: {s.agent_id}
                </p>
                {s.next_run && (
                  <p className="muted" style={{ fontSize: "0.72rem", margin: "2px 0 0" }}>
                    다음 실행: {s.next_run}
                  </p>
                )}
              </div>
              <div className="row" style={{ gap: 6 }}>
                <button
                  className="secondary"
                  style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                  onClick={() => handleRunNow(s.schedule_id)}
                  disabled={runningNow === s.schedule_id}
                >
                  {runningNow === s.schedule_id ? "실행 중…" : "즉시 실행"}
                </button>
                <button
                  className="secondary"
                  style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                  onClick={() => handleViewLogs(s.schedule_id)}
                >
                  {logsFor === s.schedule_id ? "로그 닫기" : "로그"}
                </button>
                <button
                  className="secondary"
                  style={{
                    fontSize: "0.75rem",
                    padding: "4px 10px",
                    color: "#ef4444",
                    borderColor: "#ef4444",
                  }}
                  onClick={() => handleRemove(s.schedule_id)}
                >
                  해제
                </button>
              </div>
            </div>

            {logsFor === s.schedule_id && (
              <div
                style={{
                  marginTop: 4,
                  marginLeft: 26,
                  borderLeft: "2px solid #3a3f52",
                  paddingLeft: 12,
                }}
              >
                {logs.length === 0 ? (
                  <p className="muted" style={{ fontSize: "0.78rem" }}>
                    실행 기록이 없습니다.
                  </p>
                ) : (
                  logs.map((entry, i) => (
                    <div
                      key={i}
                      className="card"
                      style={{ padding: "8px 12px", marginBottom: 6 }}
                    >
                      <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
                        <span className="muted" style={{ fontSize: "0.72rem" }}>
                          {entry.started_at}
                        </span>
                        <span
                          className="badge"
                          style={{
                            background:
                              entry.results.every((r) => r.result?.status === "success")
                                ? "#22c55e"
                                : "#ef4444",
                            fontSize: "0.68rem",
                          }}
                        >
                          {entry.results.every((r) => r.result?.status === "success")
                            ? "성공"
                            : "오류"}
                        </span>
                      </div>
                      {entry.results.map((r, j) => (
                        <p
                          key={j}
                          className="muted"
                          style={{ fontSize: "0.75rem", margin: "2px 0" }}
                        >
                          {r.tool_id}/{r.function} →{" "}
                          {(r.result as Record<string, unknown>)?.status as string ?? "?"}
                        </p>
                      ))}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
