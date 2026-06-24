"""GraphAgent 프롬프트(§7)."""

from langchain_core.prompts import ChatPromptTemplate

EXPAND_SYSTEM = """\
You are a knowledge graph expansion agent.
Given a query and existing context chunks, identify related concepts, entities, \
and relationships that would enrich the understanding of the topic.

Output a JSON object with:
- "expanded_context": a comprehensive text that connects the given context pieces, \
  identifies key entities and their relationships, and fills in gaps
- "entities": list of key entities found
- "relationships": list of relationships between entities (each: {"from", "to", "relation"})"""

EXPAND_PROMPT = ChatPromptTemplate.from_messages([
    ("system", EXPAND_SYSTEM),
    ("human", "Query:\n{query}\n\nContext chunks:\n{context}"),
])

SUMMARIZE_SYSTEM = """\
You are a summarization agent.
Given an expanded context about a topic, produce a concise but comprehensive summary.

Output a JSON object with:
- "summary": the final summary text
- "key_points": list of the most important points"""

SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SUMMARIZE_SYSTEM),
    ("human", "Query:\n{query}\n\nExpanded context:\n{expanded_context}"),
])
