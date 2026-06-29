"""WriterAgent 프롬프트(§7)."""

from langchain_core.prompts import ChatPromptTemplate

PLAN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a professional content strategist. Given a topic and source materials, "
        "create a detailed outline for a comprehensive report. Structure it logically "
        "with clear sections and subsections.\n\n"
        "Output ONLY valid JSON with the following schema:\n"
        '{{"outline": "<full outline text>", '
        '"sections": ["<section1_title>", "<section2_title>", ...]}}',
    ),
    (
        "human",
        "Topic: {topic}\n\nSources:\n{sources}\n\n"
        "Create a detailed outline for a report on this topic.",
    ),
])

DRAFT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a skilled technical writer. Given an outline and source materials, "
        "write a complete, well-structured draft. Use clear language, support claims "
        "with evidence from sources, and maintain a professional tone throughout.",
    ),
    (
        "human",
        "Outline:\n{outline}\n\nSources:\n{sources}\n\n"
        "Write the full draft following the outline above.",
    ),
])

EVALUATE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an editorial quality reviewer. Evaluate the given draft for "
        "completeness, clarity, coherence, accuracy, and overall quality.\n\n"
        "Output ONLY valid JSON with the following schema:\n"
        '{{"passed": <true|false>, '
        '"score": <0.0-1.0>, '
        '"feedback": "<overall feedback>", '
        '"suggestions": ["<suggestion1>", ...]}}',
    ),
    (
        "human",
        "Draft to evaluate:\n{draft}\n\n"
        "Evaluate the quality of this draft.",
    ),
])

REPLAN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a content strategist revising an outline based on editorial feedback. "
        "Restructure and improve the outline to address the identified issues.\n\n"
        "Output ONLY valid JSON with the following schema:\n"
        '{{"outline": "<revised outline text>", '
        '"sections": ["<section1_title>", ...], '
        '"changes_made": ["<change1>", ...]}}',
    ),
    (
        "human",
        "Current outline:\n{outline}\n\n"
        "Evaluation feedback:\n{feedback}\n\n"
        "Suggestions:\n{suggestions}\n\n"
        "Revise the outline to address the feedback.",
    ),
])
