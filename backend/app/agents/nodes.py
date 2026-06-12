"""Agent node functions for the LangGraph research pipeline.

Each function takes the shared ResearchState, performs its work, and
returns the mutated state."""

from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from app.agents.state import ResearchState
from app.agents.tools import tool_graph_explore, tool_search
from app.config import settings


def _llm_call(system: str, user: str, max_tokens: int = 1500) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


# ---------------------------------------------------------------------------
# Orchestrator — decomposes the query and decides next steps
# ---------------------------------------------------------------------------

def orchestrator_node(state: ResearchState) -> ResearchState:
    """Analyse the query, decompose into sub-tasks, decide routing."""
    system = (
        "You are a research orchestrator. Given a user query, decompose it into "
        "sub-tasks for specialized agents. Decide which agents to invoke.\n"
        "Available agents: search, graph, analyst, writer.\n"
        "Reply JSON: {\"tasks\": [\"...\"], \"next\": \"search|graph|analyst|writer\"}"
    )
    context = ""
    if state.search_results:
        context = f"\nExisting search results: {len(state.search_results)} items"
    if state.analysis:
        context = f"\nAnalysis so far: {state.analysis[:500]}"

    user = f"Query: {state.query}\nIteration: {state.iteration}{context}"
    raw = _llm_call(system, user)

    try:
        if "```" in raw:
            import re
            raw = re.sub(r"```\w*\n?", "", raw).strip()
        parsed = json.loads(raw)
        state.tasks = parsed.get("tasks", [state.query])
        state.current_step = parsed.get("next", "search")
    except (json.JSONDecodeError, KeyError):
        state.tasks = [state.query]
        state.current_step = "search"

    state.iteration += 1
    return state


# ---------------------------------------------------------------------------
# Search Agent
# ---------------------------------------------------------------------------

def search_node(state: ResearchState) -> ResearchState:
    """Run semantic search + reranking for each task."""
    for task in state.tasks:
        results = tool_search(task, top_k=5, doc_type=state.domain_filter)
        state.search_results.extend(results)

    state.current_step = "analyst"
    return state


# ---------------------------------------------------------------------------
# Graph Agent
# ---------------------------------------------------------------------------

def graph_node(state: ResearchState) -> ResearchState:
    """Explore the Neo4j knowledge graph for related concepts."""
    keywords = set()
    for r in state.search_results[:5]:
        text = r.get("text", "")
        words = text.split()[:10]
        keywords.update(w.strip(".,;:!?") for w in words if len(w) > 3)

    for kw in list(keywords)[:5]:
        related = tool_graph_explore(kw)
        if related:
            state.graph_insights.extend(related)

    state.current_step = "analyst"
    return state


# ---------------------------------------------------------------------------
# Analyst Agent
# ---------------------------------------------------------------------------

def analyst_node(state: ResearchState) -> ResearchState:
    """Analyse collected information and decide if more search is needed."""
    system = (
        "You are a research analyst. Evaluate whether the gathered information "
        "is sufficient to answer the original query. If insufficient, explain "
        "what additional information is needed.\n"
        "Reply JSON: {\"sufficient\": true/false, \"score\": 0.0-1.0, "
        "\"analysis\": \"...\", \"next\": \"writer|search\"}"
    )

    search_summary = "\n".join(
        f"- {r.get('text', '')[:200]}" for r in state.search_results[:10]
    )
    graph_summary = str(state.graph_insights[:5]) if state.graph_insights else "none"

    user = (
        f"Query: {state.query}\n\n"
        f"Search results ({len(state.search_results)}):\n{search_summary}\n\n"
        f"Graph insights: {graph_summary}"
    )

    raw = _llm_call(system, user)
    try:
        if "```" in raw:
            import re
            raw = re.sub(r"```\w*\n?", "", raw).strip()
        parsed = json.loads(raw)
        state.analysis = parsed.get("analysis", "")
        state.sufficiency_score = parsed.get("score", 0.5)

        if parsed.get("sufficient", False) or state.iteration >= state.max_iterations:
            state.current_step = "writer"
        else:
            state.current_step = parsed.get("next", "search")
    except (json.JSONDecodeError, KeyError):
        state.current_step = "writer"

    return state


# ---------------------------------------------------------------------------
# Writer Agent
# ---------------------------------------------------------------------------

def writer_node(state: ResearchState) -> ResearchState:
    """Generate the final research report in Markdown."""
    system = (
        "You are a research report writer. Create a well-structured Markdown "
        "report based on the analysis and source materials provided. Include "
        "citations and section headers. Write in the same language as the query."
    )

    search_summary = "\n".join(
        f"[{r.get('source', '?')}] {r.get('text', '')[:300]}"
        for r in state.search_results[:15]
    )

    user = (
        f"Query: {state.query}\n\n"
        f"Analysis: {state.analysis}\n\n"
        f"Source materials:\n{search_summary}"
    )

    state.report = _llm_call(system, user, max_tokens=4000)
    state.is_complete = True
    state.current_step = "done"
    return state
