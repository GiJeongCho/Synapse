"""AnalystAgent 프롬프트(§7)."""

from langchain_core.prompts import ChatPromptTemplate

ANALYZE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior research analyst. Given a topic and source materials, "
        "produce a structured analysis. Be thorough, evidence-based, and identify "
        "key patterns and insights from the sources.\n\n"
        "Output ONLY valid JSON with the following schema:\n"
        '{{"analysis": "<detailed analysis text>", '
        '"key_findings": ["<finding1>", "<finding2>", ...], '
        '"confidence": <0.0-1.0>}}',
    ),
    (
        "human",
        "Topic: {topic}\n\nSources:\n{sources}\n\n"
        "Produce a structured analysis based on the above.",
    ),
])

CRITIQUE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a critical reviewer. Evaluate the given analysis for logical gaps, "
        "unsupported claims, missing perspectives, and areas that need strengthening.\n\n"
        "Output ONLY valid JSON with the following schema:\n"
        '{{"critique": "<overall critique text>", '
        '"weaknesses": ["<weakness1>", ...], '
        '"suggestions": ["<suggestion1>", ...], '
        '"needs_refinement": <true|false>}}',
    ),
    (
        "human",
        "Analysis to critique:\n{analysis}\n\n"
        "Critically evaluate this analysis.",
    ),
])

REFINE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior analyst improving your work based on critical feedback. "
        "Address each weakness and incorporate suggestions while maintaining "
        "analytical rigor.\n\n"
        "Output ONLY valid JSON with the following schema:\n"
        '{{"refined_analysis": "<improved analysis text>", '
        '"improvements_made": ["<improvement1>", ...]}}',
    ),
    (
        "human",
        "Original analysis:\n{analysis}\n\n"
        "Critique received:\n{critique}\n\n"
        "Refine the analysis addressing the critique.",
    ),
])
