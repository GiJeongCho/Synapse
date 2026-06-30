// ── 문서 업로드 ──
export interface UploadResult {
  source: string;
  doc_type: string;
  extraction_method: string;
  chunker_used: string;
  num_chunks: number;
  metrics_summary: Record<string, number>;
  all_chunker_metrics: Record<string, Record<string, number>>;
}

export interface DocumentItem {
  source: string;
  doc_type: string;
}

// ── 에이전트 ──
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
  id: string;
  text: string;
  score: number;
  final_score: number;
  rrf_score: number;
  source: string;
  doc_type: string;
  importance: string;
  importance_score: number;
  metadata?: Record<string, unknown>;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
}


// ── 워크플로우 흐름도 ──
export interface FlowNodeData {
  label: string;
  desc: string;
}

export interface FlowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: FlowNodeData;
  style?: Record<string, unknown>;
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
  style?: Record<string, unknown>;
  labelStyle?: Record<string, unknown>;
  labelBgStyle?: Record<string, unknown>;
  labelBgPadding?: [number, number];
  labelBgBorderRadius?: number;
}

export interface WorkflowGraph {
  workflow_name?: string;
  agent_id?: string;
  display_name: string;
  category: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
}

export interface WorkflowListItem {
  name: string;
  display_name: string;
  category: string;
}

// ── 도구 ──
export interface GeneratedTool {
  tool_id: string;
  name?: string;
  description?: string;
  agent_id?: string;
  functions?: string[];
  path?: string;
  has_code?: boolean;
  code?: string;
}

export interface ToolListResponse {
  tools: GeneratedTool[];
  total: number;
}

export interface ToolExecuteResult {
  status: string;
  result?: Record<string, unknown>;
  error?: string;
}
