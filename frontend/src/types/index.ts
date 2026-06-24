/** 공통 TS 타입 */

export interface AgentRecord {
  agent_id: string;
  user_request: string;
  mode: "solo" | "dual" | "reuse";
  version: number;
  created_at: string;
  agent_spec?: Record<string, unknown>;
  system_prompt?: string;
  mcp_tools?: Record<string, unknown>[];
  project_files?: Record<string, unknown>;
  test_result?: Record<string, unknown>;
}

export interface CreateAgentRequest {
  user_request: string;
  critic_enabled?: boolean;
  max_rounds?: number;
}

export interface CreateAgentResponse {
  agent_id: string;
  mode: string;
  registry_hit: boolean;
  result: Record<string, unknown>;
}

export interface RegistryListResponse {
  agents: AgentRecord[];
  total: number;
}

export interface SearchResult {
  chunk_id: string;
  text: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
}
