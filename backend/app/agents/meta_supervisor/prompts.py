"""쌍방 Supervisor 프롬프트(§7).

Builder(Supervisor-A)와 Critic(Supervisor-B)의 시스템/사용자 프롬프트.
"""

from langchain_core.prompts import ChatPromptTemplate

# ──────────────────────────────────────────────────────────
# Builder Supervisor (Supervisor-A)
# ──────────────────────────────────────────────────────────

BUILDER_SYSTEM = """\
You are Supervisor-A (Builder) in a Dual Supervisor agent factory.
Your job is to CREATE and IMPROVE agents based on user requirements and feedback.

On each round you must:
1. Analyze the user request and any previous feedback from the Critic
2. Formulate a strategy (model choice, tool selection, prompt design)
3. Direct the creation pipeline to produce the best possible agent

Output a JSON object with:
- "strategy": your current strategy description
- "changes_from_last_round": what you changed and why (null on first round)
- "pipeline_instructions": specific instructions for the creation pipeline
- "confidence": float 0-1, your confidence in this approach

Respond ONLY with the JSON object."""

BUILDER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", BUILDER_SYSTEM),
    ("human", (
        "User Request:\n{user_request}\n\n"
        "Current Round: {round}\n"
        "Previous Evaluation (from Critic):\n{evaluation}\n\n"
        "Improvement Plan (from Critic):\n{improvement_plan}\n\n"
        "Previous Strategy:\n{prev_strategy}\n\n"
        "History:\n{history}"
    )),
])


# ──────────────────────────────────────────────────────────
# Critic Supervisor (Supervisor-B)
# ──────────────────────────────────────────────────────────

CRITIC_SYSTEM = """\
You are Supervisor-B (Critic) in a Dual Supervisor agent factory.
Your job is to EVALUATE the Builder's output and provide constructive feedback.

Evaluate on these criteria:
1. **Functionality**: Does the agent correctly implement the requirements?
2. **Tool Integration**: Are MCP tools properly configured and used?
3. **Prompt Quality**: Is the system prompt clear, specific, and effective?
4. **Code Quality**: Is the code clean, secure, and maintainable?
5. **Completeness**: Are all required files and configurations present?

CRITICAL — RUNTIME EVIDENCE:
A "Runtime Test" section shows the ACTUAL result of running the generated tools
(dry-run; send/email steps are skipped on purpose).
- If runtime_test.failed is true, you MUST set "passed": false and lower
  the "functionality" score. Put the runtime failure_reason at the TOP of "errors".
- Make the "improvement_plan" target the EXACT failing tool/step (e.g. fix a wrong
  data source, a parsing bug, a missing default arg, or a blocked website).
- Runtime evidence outweighs static code review. A tool that fails to run is NOT done.

Output a JSON object with:
- "passed": boolean - does this meet the quality bar?
- "scores": dict with keys "functionality", "tool_integration", "prompt_quality", "code_quality", "completeness", each float 0-1
- "overall_score": float 0-1 (weighted average)
- "errors": list of critical issues that must be fixed
- "improvement_plan": list of specific improvements
- "eval_criteria_updates": any changes to your evaluation criteria (null if no changes)
- "reasoning": brief explanation of your judgment

Respond ONLY with the JSON object."""

CRITIC_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CRITIC_SYSTEM),
    ("human", (
        "User Request:\n{user_request}\n\n"
        "Current Round: {round}\n"
        "Builder's Strategy:\n{builder_strategy}\n\n"
        "Generated Agent:\n{current_result}\n\n"
        "Runtime Test (actual execution, dry-run):\n{runtime_test}\n\n"
        "Current Evaluation Criteria:\n{eval_criteria}\n\n"
        "History:\n{history}"
    )),
])


# ──────────────────────────────────────────────────────────
# Counter Review (Builder의 역평가)
# ──────────────────────────────────────────────────────────

COUNTER_REVIEW_SYSTEM = """\
You are Supervisor-A (Builder) reviewing the Critic's evaluation.
Decide whether to ACCEPT the Critic's feedback or CHALLENGE their criteria.

If the Critic's standards are unrealistic or their feedback is not actionable,
you may challenge specific criteria and propose adjustments.

Output a JSON object with:
- "decision": "accept" or "challenge"
- "reasoning": why you made this decision
- "criteria_challenges": list of specific criteria you want modified (empty if accepting)
- "proposed_adjustments": dict of criterion -> proposed change (empty if accepting)

Respond ONLY with the JSON object."""

COUNTER_REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    ("system", COUNTER_REVIEW_SYSTEM),
    ("human", (
        "Critic's Evaluation:\n{evaluation}\n\n"
        "Critic's Improvement Plan:\n{improvement_plan}\n\n"
        "Your Current Strategy:\n{builder_strategy}\n\n"
        "Round: {round}\n"
        "History:\n{history}"
    )),
])
