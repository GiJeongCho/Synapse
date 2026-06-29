import type { Node, Edge } from "reactflow";

const nodeBase = {
  type: "flowCard",
  style: { width: 180 },
};

const edgeDefaults = {
  style: { stroke: "#5a6278", strokeWidth: 2 },
  labelStyle: { fill: "#c8cdd8", fontSize: 11, fontWeight: 600 },
  labelBgStyle: { fill: "#1a1e2c", stroke: "#3a3f52", strokeWidth: 1 },
  labelBgPadding: [6, 4] as [number, number],
  labelBgBorderRadius: 4,
};

/** Meta-Agent 파이프라인 4-노드 */
export const pipelineNodes: Node[] = [
  { ...nodeBase, id: "req", position: { x: 0, y: 0 }, data: { label: "Requirements Analyzer", desc: "요구사항 분석 → 에이전트 스펙 생성" } },
  { ...nodeBase, id: "tool", position: { x: 250, y: 0 }, data: { label: "Tool Retriever", desc: "MCP Registry에서 필요한 도구 검색" } },
  { ...nodeBase, id: "prov", position: { x: 500, y: 0 }, data: { label: "Provisioner", desc: "코드·프롬프트 생성" } },
  { ...nodeBase, id: "eval", position: { x: 750, y: 0 }, data: { label: "Evaluator", desc: "코드 검증 + 재시도 판단" } },
];

export const pipelineEdges: Edge[] = [
  { ...edgeDefaults, id: "e-req-tool", source: "req", target: "tool", animated: true },
  { ...edgeDefaults, id: "e-tool-prov", source: "tool", target: "prov", animated: true },
  { ...edgeDefaults, id: "e-prov-eval", source: "prov", target: "eval", animated: true },
  { ...edgeDefaults, id: "e-eval-req", source: "eval", target: "req", label: "retry", style: { stroke: "#ef4444", strokeWidth: 2 }, animated: true },
];

/** Dual Supervisor 루프 */
export const supervisorNodes: Node[] = [
  { ...nodeBase, id: "builder", position: { x: 0, y: 0 }, data: { label: "Builder (Supervisor-A)", desc: "에이전트 생성 파이프라인 실행" } },
  { ...nodeBase, id: "critic", position: { x: 300, y: 0 }, data: { label: "Critic (Supervisor-B)", desc: "빌더 결과 평가 + 개선안 제시" } },
  { ...nodeBase, id: "counter", position: { x: 150, y: 120 }, data: { label: "Counter Review", desc: "빌더가 비평에 반론/수용" } },
  { ...nodeBase, id: "consensus", position: { x: 150, y: 240 }, data: { label: "Consensus Check", desc: "합의 여부 판단" } },
];

export const supervisorEdges: Edge[] = [
  { ...edgeDefaults, id: "e-b-cr", source: "builder", target: "critic", animated: true },
  { ...edgeDefaults, id: "e-cr-co", source: "critic", target: "counter", animated: true },
  { ...edgeDefaults, id: "e-co-cs", source: "counter", target: "consensus", animated: true },
  { ...edgeDefaults, id: "e-cs-b", source: "consensus", target: "builder", label: "다음 라운드", style: { stroke: "#f59e0b", strokeWidth: 2 }, animated: true },
];

/** 전체 오케스트레이터 */
export const orchestratorNodes: Node[] = [
  { ...nodeBase, id: "entry", position: { x: 0, y: 80 }, data: { label: "사용자 요청", desc: "에이전트 생성 요청 수신" } },
  { ...nodeBase, id: "registry", position: { x: 220, y: 80 }, data: { label: "Registry Lookup", desc: "기존 에이전트 검색" } },
  { ...nodeBase, id: "reuse", position: { x: 440, y: 0 }, data: { label: "에이전트 재사용", desc: "Registry HIT → 즉시 반환" } },
  { ...nodeBase, id: "solo", position: { x: 440, y: 80 }, data: { label: "Solo 모드", desc: "Builder 1회 실행" } },
  { ...nodeBase, id: "dual", position: { x: 440, y: 160 }, data: { label: "Dual 모드", desc: "Builder ↔ Critic 루프" } },
  { ...nodeBase, id: "result", position: { x: 680, y: 80 }, data: { label: "결과 반환", desc: "생성된 에이전트 반환" } },
];

export const orchestratorEdges: Edge[] = [
  { ...edgeDefaults, id: "e-en-reg", source: "entry", target: "registry", animated: true },
  { ...edgeDefaults, id: "e-reg-reuse", source: "registry", target: "reuse", label: "HIT", style: { stroke: "#22c55e", strokeWidth: 2 } },
  { ...edgeDefaults, id: "e-reg-solo", source: "registry", target: "solo", label: "MISS + Solo" },
  { ...edgeDefaults, id: "e-reg-dual", source: "registry", target: "dual", label: "MISS + Dual", style: { stroke: "#a855f7", strokeWidth: 2 } },
  { ...edgeDefaults, id: "e-reuse-res", source: "reuse", target: "result" },
  { ...edgeDefaults, id: "e-solo-res", source: "solo", target: "result" },
  { ...edgeDefaults, id: "e-dual-res", source: "dual", target: "result" },
];

/** 리서치 워크플로우 */
export const researchNodes: Node[] = [
  { ...nodeBase, id: "r-sup", position: { x: 300, y: 0 }, data: { label: "Research Supervisor", desc: "다음 에이전트를 결정" } },
  { ...nodeBase, id: "r-search", position: { x: 0, y: 120 }, data: { label: "Search Agent", desc: "벡터 검색 수행" } },
  { ...nodeBase, id: "r-crawl", position: { x: 160, y: 120 }, data: { label: "Crawl Agent", desc: "URL 크롤링" } },
  { ...nodeBase, id: "r-graph", position: { x: 320, y: 120 }, data: { label: "Graph Agent", desc: "지식그래프 확장" } },
  { ...nodeBase, id: "r-analyst", position: { x: 480, y: 120 }, data: { label: "Analyst Agent", desc: "분석·비판·개선" } },
  { ...nodeBase, id: "r-writer", position: { x: 640, y: 120 }, data: { label: "Writer Agent", desc: "보고서 작성" } },
  { ...nodeBase, id: "r-finish", position: { x: 300, y: 240 }, data: { label: "FINISH", desc: "최종 보고서 반환" } },
];

export const researchEdges: Edge[] = [
  { ...edgeDefaults, id: "re-s-se", source: "r-sup", target: "r-search", animated: true },
  { ...edgeDefaults, id: "re-s-cr", source: "r-sup", target: "r-crawl", animated: true },
  { ...edgeDefaults, id: "re-s-gr", source: "r-sup", target: "r-graph", animated: true },
  { ...edgeDefaults, id: "re-s-an", source: "r-sup", target: "r-analyst", animated: true },
  { ...edgeDefaults, id: "re-s-wr", source: "r-sup", target: "r-writer", animated: true },
  { ...edgeDefaults, id: "re-se-s", source: "r-search", target: "r-sup", style: { stroke: "#6b7280", strokeWidth: 2 } },
  { ...edgeDefaults, id: "re-cr-s", source: "r-crawl", target: "r-sup", style: { stroke: "#6b7280", strokeWidth: 2 } },
  { ...edgeDefaults, id: "re-gr-s", source: "r-graph", target: "r-sup", style: { stroke: "#6b7280", strokeWidth: 2 } },
  { ...edgeDefaults, id: "re-an-s", source: "r-analyst", target: "r-sup", style: { stroke: "#6b7280", strokeWidth: 2 } },
  { ...edgeDefaults, id: "re-wr-s", source: "r-writer", target: "r-sup", style: { stroke: "#6b7280", strokeWidth: 2 } },
  { ...edgeDefaults, id: "re-s-f", source: "r-sup", target: "r-finish", label: "FINISH", style: { stroke: "#22c55e", strokeWidth: 2 } },
];
