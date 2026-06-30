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
  UploadResult,
  DocumentItem,
} from "../types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 600_000,
});

// ── 문서 업로드 ──
export async function uploadDocument(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<UploadResult>("/api/documents/upload", form);
  return data;
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const { data } = await api.get<DocumentItem[]>("/api/documents/list");
  return data;
}

export async function deleteDocument(source: string): Promise<void> {
  await api.delete(`/api/documents/${encodeURIComponent(source)}`);
}

export interface GraphNodeData {
  id: string;
  node_type: "Document" | "Article" | "Chunk";
  label: string;
  sub: string;
  properties: Record<string, unknown>;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  rel_type: "HAS_CHUNK" | "HAS_ARTICLE" | "NEXT_CHUNK" | "NEXT_ARTICLE";
}

export interface DocumentGraphResponse {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
}

export async function getDocumentGraph(source: string): Promise<DocumentGraphResponse> {
  const { data } = await api.get<DocumentGraphResponse>(`/api/documents/graph/${encodeURIComponent(source)}`);
  return data;
}

export async function getDocumentChunks(source: string): Promise<Record<string, unknown>[]> {
  const { data } = await api.get(`/api/documents/chunks/${encodeURIComponent(source)}`);
  return data;
}

export async function editChunk(
  chunkId: string,
  newText: string,
  source: string,
  docType: string,
): Promise<void> {
  await api.post("/api/documents/chunks/edit", {
    chunk_id: chunkId,
    new_text: newText,
    source,
    doc_type: docType,
  });
}

export async function deleteChunks(chunkIds: string[]): Promise<void> {
  await api.post("/api/documents/chunks/delete", { chunk_ids: chunkIds });
}

// ── 에이전트 ──
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

export async function deleteAgent(agentId: string): Promise<{
  status: string;
  agent_id: string;
  tools_deleted: number;
  protected_tools?: { tool_id: string; reason: string }[];
  kept_tools?: { tool_id: string; reason: string }[];
}> {
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
    failed?: boolean;
    failure_reason?: string;
    failed_checks?: { capability: string; label: string; ok: boolean; hint: string }[];
    results: { tool_id: string; function: string; result: Record<string, unknown>; reason?: string }[];
  };
}

export async function searchDocuments(
  query: string,
  topK = 10,
  docTypeFilter?: string,
  importanceFilter?: string,
): Promise<SearchResponse> {
  const { data } = await api.post<SearchResponse>("/api/search/query", {
    query,
    top_k: topK,
    doc_type_filter: docTypeFilter,
    importance_filter: importanceFilter,
  });
  return data;
}

// ── 워크플로우 ──
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

// ── 도구 ──
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

// ── 스케줄 ──
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
  return data as {
    status: string;
    schedule_id: string;
    agent_id?: string;
    pipeline_status?: string;
    failed?: boolean;
    failure_reason?: string;
    results?: { tool_id: string; function: string; result: Record<string, unknown>; reason?: string }[];
  };
}
