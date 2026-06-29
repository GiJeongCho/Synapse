"""워커 노드(§10.1) — 각 에이전트 서브그래프를 호출하고 결과를 State에 병합한다."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.core.logging import logger
from app.workflows.research.state import ResearchState

log = logger(__name__)


async def _run_subgraph(
    agent_name: str,
    create_fn,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """에이전트 서브그래프를 실행하고 결과를 반환한다."""
    try:
        workflow = create_fn()
        result = await workflow.ainvoke(input_data)
        return {"agent": agent_name, "status": "success", "data": result}
    except Exception as exc:
        log.error("%s 실행 실패: %s", agent_name, exc, exc_info=True)
        return {"agent": agent_name, "status": "error", "error": str(exc)}


async def search_worker(
    state: ResearchState,
    config: RunnableConfig,
) -> dict[str, Any]:
    from app.agents.search_agent.graph import create_search_workflow

    instruction = state.get("instruction", state.get("topic", ""))
    result = await _run_subgraph(
        "search",
        create_search_workflow,
        {"job_id": state.get("job_id", ""), "query": instruction},
    )
    log.info("Search worker 완료: status=%s", result["status"])
    return {"search_result": result, "results": [result]}


async def crawl_worker(
    state: ResearchState,
    config: RunnableConfig,
) -> dict[str, Any]:
    from app.agents.crawl_agent.graph import create_crawl_workflow

    instruction = state.get("instruction", "")
    result = await _run_subgraph(
        "crawl",
        create_crawl_workflow,
        {"job_id": state.get("job_id", ""), "url": instruction},
    )
    log.info("Crawl worker 완료: status=%s", result["status"])
    return {"crawl_result": result, "results": [result]}


async def graph_worker(
    state: ResearchState,
    config: RunnableConfig,
) -> dict[str, Any]:
    from app.agents.graph_agent.graph import create_graph_workflow

    instruction = state.get("instruction", state.get("topic", ""))
    context = []
    for r in state.get("results", []):
        if r.get("status") == "success" and r.get("data"):
            context.append(r["data"])

    result = await _run_subgraph(
        "graph",
        create_graph_workflow,
        {"job_id": state.get("job_id", ""), "query": instruction, "context": context},
    )
    log.info("Graph worker 완료: status=%s", result["status"])
    return {"graph_result": result, "results": [result]}


async def analyst_worker(
    state: ResearchState,
    config: RunnableConfig,
) -> dict[str, Any]:
    from app.agents.analyst_agent.graph import create_analyst_workflow

    topic = state.get("topic", "")
    sources = [
        r["data"]
        for r in state.get("results", [])
        if r.get("status") == "success" and r.get("data")
    ]

    result = await _run_subgraph(
        "analyst",
        create_analyst_workflow,
        {"job_id": state.get("job_id", ""), "topic": topic, "sources": sources},
    )
    log.info("Analyst worker 완료: status=%s", result["status"])
    return {"analyst_result": result, "results": [result]}


async def writer_worker(
    state: ResearchState,
    config: RunnableConfig,
) -> dict[str, Any]:
    from app.agents.writer_agent.graph import create_writer_workflow

    topic = state.get("topic", "")
    sources = [
        r["data"]
        for r in state.get("results", [])
        if r.get("status") == "success" and r.get("data")
    ]

    result = await _run_subgraph(
        "writer",
        create_writer_workflow,
        {"job_id": state.get("job_id", ""), "topic": topic, "sources": sources},
    )

    final_text = ""
    if result.get("status") == "success" and result.get("data"):
        final_text = result["data"].get("final_text", result["data"].get("draft", ""))

    log.info("Writer worker 완료: status=%s", result["status"])
    return {"writer_result": result, "results": [result], "final_report": final_text}
