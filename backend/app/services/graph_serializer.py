"""LangGraph 워크플로우 → React Flow JSON 변환 유틸리티.

컴파일된 LangGraph에서 노드/엣지 구조를 추출하여
프론트엔드 React Flow가 소비할 수 있는 JSON으로 변환한다.
"""

from __future__ import annotations

import math
from typing import Any


def extract_graph_structure(
    compiled_graph,
    *,
    descriptions: dict[str, str] | None = None,
    layout: str = "auto",
) -> dict[str, Any]:
    """CompiledGraph에서 노드/엣지를 추출하여 React Flow 호환 JSON을 반환한다.

    Args:
        compiled_graph: langgraph.graph.StateGraph.compile() 반환값.
        descriptions: 노드 ID → 설명 매핑 (선택).
        layout: "auto" | "horizontal" | "vertical".

    Returns:
        {"nodes": [...], "edges": [...]}
    """
    descriptions = descriptions or {}
    graph = compiled_graph.get_graph()

    raw_nodes: list[str] = []
    raw_edges: list[dict] = []

    for node in graph.nodes:
        if node in ("__start__", "__end__"):
            continue
        raw_nodes.append(node)

    for edge in graph.edges:
        src = edge.source
        tgt = edge.target

        if src == "__start__":
            src = "__entry__"
        if tgt == "__end__":
            tgt = "__exit__"

        label = ""
        if hasattr(edge, "data") and edge.data:
            label = str(edge.data)
        if hasattr(edge, "conditional") and edge.conditional:
            label = label or "conditional"

        raw_edges.append({"source": src, "target": tgt, "label": label})

    all_node_ids = set(raw_nodes)

    needs_entry = any(e["source"] == "__entry__" for e in raw_edges)
    needs_exit = any(e["target"] == "__exit__" for e in raw_edges)

    if needs_entry:
        all_node_ids.add("__entry__")
    if needs_exit:
        all_node_ids.add("__exit__")

    node_list = sorted(all_node_ids)
    positions = _compute_positions(node_list, raw_edges, layout)

    flow_nodes = []
    for nid in node_list:
        label = nid
        desc = descriptions.get(nid, "")

        if nid == "__entry__":
            label = "START"
            desc = "워크플로우 시작점"
        elif nid == "__exit__":
            label = "END"
            desc = "워크플로우 종료점"

        flow_nodes.append({
            "id": nid,
            "type": "flowCard",
            "position": positions.get(nid, {"x": 0, "y": 0}),
            "data": {"label": label, "desc": desc},
            "style": {"width": 180},
        })

    flow_edges = []
    for i, e in enumerate(raw_edges):
        src = e["source"]
        tgt = e["target"]

        if src not in all_node_ids or tgt not in all_node_ids:
            continue

        edge_data: dict[str, Any] = {
            "id": f"e-{i}-{src}-{tgt}",
            "source": src,
            "target": tgt,
            "animated": True,
            "style": {"stroke": "#5a6278", "strokeWidth": 2},
            "labelStyle": {"fill": "#c8cdd8", "fontSize": 11, "fontWeight": 600},
            "labelBgStyle": {"fill": "#1a1e2c", "stroke": "#3a3f52", "strokeWidth": 1},
            "labelBgPadding": [6, 4],
            "labelBgBorderRadius": 4,
        }

        if e["label"] and e["label"] != "conditional":
            edge_data["label"] = e["label"]

        if "retry" in e.get("label", "").lower():
            edge_data["style"] = {"stroke": "#ef4444", "strokeWidth": 2}
        elif "finish" in e.get("label", "").lower():
            edge_data["style"] = {"stroke": "#22c55e", "strokeWidth": 2}

        flow_edges.append(edge_data)

    return {"nodes": flow_nodes, "edges": flow_edges}


def _compute_positions(
    node_ids: list[str],
    edges: list[dict],
    layout: str,
) -> dict[str, dict[str, int]]:
    """간단한 자동 레이아웃으로 노드 위치를 계산한다."""
    if not node_ids:
        return {}

    adjacency: dict[str, list[str]] = {n: [] for n in node_ids}
    in_degree: dict[str, int] = {n: 0 for n in node_ids}

    for e in edges:
        src, tgt = e["source"], e["target"]
        if src in adjacency and tgt in adjacency:
            adjacency[src].append(tgt)
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    levels: dict[str, int] = {}
    queue = [n for n in node_ids if in_degree.get(n, 0) == 0]

    if not queue:
        queue = [node_ids[0]]

    for n in queue:
        levels[n] = 0

    visited = set(queue)
    idx = 0
    while idx < len(queue):
        current = queue[idx]
        idx += 1
        for child in adjacency.get(current, []):
            if child not in visited:
                levels[child] = levels[current] + 1
                visited.add(child)
                queue.append(child)

    for n in node_ids:
        if n not in levels:
            levels[n] = max(levels.values(), default=0) + 1

    level_groups: dict[int, list[str]] = {}
    for n, lv in levels.items():
        level_groups.setdefault(lv, []).append(n)

    x_gap = 240
    y_gap = 100

    positions = {}
    for lv, members in level_groups.items():
        total_height = (len(members) - 1) * y_gap
        start_y = -total_height // 2

        for i, n in enumerate(sorted(members)):
            positions[n] = {"x": lv * x_gap, "y": start_y + i * y_gap}

    return positions


# ──────────────────────────────────────────────────────────
# 내장 워크플로우 레지스트리
# ──────────────────────────────────────────────────────────

_BUILTIN_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "search_agent": {
        "search": "벡터 DB에서 유사 문서 검색",
        "filter": "유사도 임계값 기반 필터링",
        "organize": "LLM으로 결과를 주제별 그룹화",
        "evaluate": "검색 결과 충분성 평가",
    },
    "crawl_agent": {
        "fetch": "URL에서 콘텐츠 가져오기",
        "extract": "HTML에서 본문 텍스트 추출",
        "normalize": "텍스트 정규화·정리",
    },
    "graph_agent": {
        "expand": "관련 개념·엔티티 확장",
        "summarize": "확장된 컨텍스트 요약",
    },
    "analyst_agent": {
        "analyze": "주제와 소스를 기반으로 분석",
        "critique": "분석 결과 자기비판",
        "refine": "비평 반영하여 분석 개선",
    },
    "writer_agent": {
        "plan": "아웃라인 생성",
        "draft": "초안 작성",
        "evaluate": "초안 품질 평가",
        "replan": "평가 피드백 반영 재계획",
        "finalize": "최종 텍스트 확정",
    },
    "research_supervisor": {
        "supervisor": "다음 실행할 에이전트를 결정",
        "search": "Search Agent 서브그래프 실행",
        "crawl": "Crawl Agent 서브그래프 실행",
        "graph": "Graph Agent 서브그래프 실행",
        "analyst": "Analyst Agent 서브그래프 실행",
        "writer": "Writer Agent 서브그래프 실행",
    },
    "meta_agent_pipeline": {
        "requirements_analyzer": "요구사항 분석 → 에이전트 스펙 생성",
        "tool_retriever": "MCP Registry에서 필요한 도구 검색",
        "provisioner": "코드·프롬프트 생성",
        "evaluator": "코드 검증 + 재시도 판단",
    },
    "dual_supervisor": {
        "registry_lookup": "기존 에이전트 검색 (Registry)",
        "builder_supervisor": "에이전트 생성 파이프라인 실행",
        "critic_supervisor": "빌더 결과 평가 + 개선안 제시",
        "counter_review": "빌더가 비평에 반론/수용",
        "consensus_check": "합의 여부 판단",
    },
}


def get_builtin_workflow_graph(workflow_name: str) -> dict[str, Any] | None:
    """내장 워크플로우 이름으로 그래프 구조를 추출한다.

    워크플로우 생성 함수를 호출하고 graph 구조를 직렬화한다.
    실패 시 None을 반환한다.
    """
    descriptions = _BUILTIN_DESCRIPTIONS.get(workflow_name, {})

    try:
        if workflow_name == "search_agent":
            from app.agents.search_agent.graph import create_search_workflow
            compiled = create_search_workflow()
        elif workflow_name == "crawl_agent":
            from app.agents.crawl_agent.graph import create_crawl_workflow
            compiled = create_crawl_workflow()
        elif workflow_name == "graph_agent":
            from app.agents.graph_agent.graph import create_graph_workflow
            compiled = create_graph_workflow()
        elif workflow_name == "analyst_agent":
            from app.agents.analyst_agent.graph import create_analyst_workflow
            compiled = create_analyst_workflow()
        elif workflow_name == "writer_agent":
            from app.agents.writer_agent.graph import create_writer_workflow
            compiled = create_writer_workflow()
        elif workflow_name == "research_supervisor":
            from app.workflows.research.graph import create_research_workflow
            compiled = create_research_workflow()
        elif workflow_name == "meta_agent_pipeline":
            from app.agents.meta_agent.graph import create_meta_agent_workflow
            compiled = create_meta_agent_workflow()
        elif workflow_name == "dual_supervisor":
            from app.agents.meta_supervisor.graph import create_dual_supervisor_workflow
            compiled = create_dual_supervisor_workflow()
        else:
            return None

        result = extract_graph_structure(compiled, descriptions=descriptions)
        result["workflow_name"] = workflow_name
        result["display_name"] = _DISPLAY_NAMES.get(workflow_name, workflow_name)
        result["category"] = _CATEGORIES.get(workflow_name, "기타")
        return result
    except Exception:
        return None


_DISPLAY_NAMES: dict[str, str] = {
    "search_agent": "Search Agent",
    "crawl_agent": "Crawl Agent",
    "graph_agent": "Graph Agent",
    "analyst_agent": "Analyst Agent",
    "writer_agent": "Writer Agent",
    "research_supervisor": "Research Supervisor",
    "meta_agent_pipeline": "Meta-Agent 파이프라인",
    "dual_supervisor": "Dual Supervisor",
}

_CATEGORIES: dict[str, str] = {
    "search_agent": "워커 에이전트",
    "crawl_agent": "워커 에이전트",
    "graph_agent": "워커 에이전트",
    "analyst_agent": "워커 에이전트",
    "writer_agent": "워커 에이전트",
    "research_supervisor": "오케스트레이션",
    "meta_agent_pipeline": "메타 에이전트",
    "dual_supervisor": "메타 에이전트",
}

BUILTIN_WORKFLOW_NAMES = list(_DISPLAY_NAMES.keys())
