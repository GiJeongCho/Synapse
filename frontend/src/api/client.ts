import axios from "axios";
import type {
  CreateAgentRequest,
  CreateAgentResponse,
  RegistryListResponse,
  AgentRecord,
  SearchResponse,
  WorkflowGraph,
  WorkflowListItem,
  ToolListResponse,
  GeneratedTool,
  ToolExecuteResult,
} from "../types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  timeout: 600_000,
});

export async function createAgent(
  req: CreateAgentRequest,
): Promise<CreateAgentResponse> {
  const { data } = await api.post<CreateAgentResponse>(
    "/api/meta-agent/create",
    req,
  );
  return data;
}

export async function listRegistry(): Promise<RegistryListResponse> {
  const { data } = await api.get<RegistryListResponse>(
    "/api/meta-agent/registry",
  );
  return data;
}

export async function getAgentDetail(
  agentId: string,
): Promise<AgentRecord> {
  const { data } = await api.get<AgentRecord>(
    `/api/meta-agent/registry/${agentId}`,
  );
  return data;
}

export async function deleteAgent(
  agentId: string,
): Promise<{ status: string; agent_id: string; tools_deleted: number }> {
  const { data } = await api.delete(`/api/meta-agent/registry/${agentId}`);
  return data;
}

export async function checkAgentPrereqs(agentId: string) {
  const { data } = await api.get(`/api/meta-agent/registry/${agentId}/prereqs`);
  return data as {
    agent_id: string;
    all_ok: boolean;
    checks: { capability: string; label: string; ok: boolean; hint: string }[];
    tool_count: number;
  };
}

export async function runAgent(agentId: string) {
  const { data } = await api.post(`/api/meta-agent/registry/${agentId}/run`);
  return data as {
    status: string;
    agent_id?: string;
    message?: string;
    failed_checks?: { capability: string; label: string; ok: boolean; hint: string }[];
    results: { tool_id: string; function: string; result: Record<string, unknown> }[];
  };
}

export async function searchDocuments(
  query: string,
  topK = 10,
): Promise<SearchResponse> {
  const { data } = await api.post<SearchResponse>("/api/search/query", {
    query,
    top_k: topK,
  });
  return data;
}

export async function listBuiltinWorkflows(): Promise<WorkflowListItem[]> {
  const { data } = await api.get<WorkflowListItem[]>(
    "/api/workflows/builtin",
  );
  return data;
}

export async function getBuiltinWorkflowGraph(
  workflowName: string,
): Promise<WorkflowGraph> {
  const { data } = await api.get<WorkflowGraph>(
    `/api/workflows/builtin/${workflowName}`,
  );
  return data;
}

export async function getAgentWorkflowGraph(
  agentId: string,
): Promise<WorkflowGraph> {
  const { data } = await api.get<WorkflowGraph>(
    `/api/workflows/agent/${agentId}`,
  );
  return data;
}

export async function listGeneratedTools(): Promise<ToolListResponse> {
  const { data } = await api.get<ToolListResponse>("/api/tools/list");
  return data;
}

export async function getToolDetail(
  toolId: string,
): Promise<GeneratedTool> {
  const { data } = await api.get<GeneratedTool>(`/api/tools/${toolId}`);
  return data;
}

// ── 스케줄 API ──

export async function listSchedules() {
  const { data } = await api.get("/api/schedules/list");
  return data as { schedules: any[]; total: number };
}

export async function registerSchedule(
  agentId: string,
  cron: string,
  description = "",
) {
  const { data } = await api.post("/api/schedules/register", {
    agent_id: agentId,
    cron,
    description,
  });
  return data;
}

export async function removeSchedule(scheduleId: string) {
  const { data } = await api.delete(`/api/schedules/${scheduleId}`);
  return data;
}

export async function getScheduleLogs(scheduleId: string, limit = 20) {
  const { data } = await api.get(`/api/schedules/${scheduleId}/logs`, {
    params: { limit },
  });
  return data as { logs: any[]; total: number };
}

export async function runScheduleNow(scheduleId: string) {
  const { data } = await api.post(`/api/schedules/${scheduleId}/run-now`);
  return data;
}

export async function executeTool(
  toolId: string,
  functionName: string,
  args: Record<string, unknown> = {},
  timeout = 60,
): Promise<ToolExecuteResult> {
  const { data } = await api.post<ToolExecuteResult>(
    `/api/tools/${toolId}/execute`,
    { function_name: functionName, arguments: args, timeout },
  );
  return data;
}
