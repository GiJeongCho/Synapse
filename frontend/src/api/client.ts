import axios from "axios";
import type {
  CreateAgentRequest,
  CreateAgentResponse,
  RegistryListResponse,
  AgentRecord,
  SearchResponse,
} from "../types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 120_000,
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
