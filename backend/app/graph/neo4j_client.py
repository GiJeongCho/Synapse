"""Neo4j graph DB client — stores document/concept/entity nodes and
relationships with configurable granularity.

Relationship granularity strategies:
- word-sentence: keyword nodes linked to the sentence chunks containing them
- sentence-sentence: chunks linked to co-occurring/sequential chunks
- word-word: co-occurrence graph between keywords within the same document
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from neo4j import GraphDatabase

from app.config import settings

_driver = None


class RelationGranularity(str, Enum):
    WORD_SENTENCE = "word_sentence"
    SENTENCE_SENTENCE = "sentence_sentence"
    WORD_WORD = "word_word"


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_schema() -> None:
    """Create indexes and constraints for the graph schema."""
    driver = get_driver()
    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.source IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE")
        session.run("CREATE INDEX IF NOT EXISTS FOR (ch:Chunk) ON (ch.chunk_id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (k:Keyword) ON (k.name)")


# ---------------------------------------------------------------------------
# Document & Chunk nodes
# ---------------------------------------------------------------------------

def upsert_document(source: str, doc_type: str, metadata: dict[str, Any] | None = None) -> None:
    """Create or update a Document node."""
    driver = get_driver()
    props = {"source": source, "doc_type": doc_type}
    if metadata:
        props.update(metadata)
    with driver.session() as session:
        session.run(
            "MERGE (d:Document {source: $source}) "
            "SET d += $props",
            source=source,
            props=props,
        )


def upsert_chunk_node(chunk_id: str, source: str, text_preview: str, importance: str) -> None:
    """Create a Chunk node and link it to its Document."""
    driver = get_driver()
    with driver.session() as session:
        session.run(
            "MERGE (ch:Chunk {chunk_id: $chunk_id}) "
            "SET ch.text_preview = $preview, ch.importance = $importance "
            "WITH ch "
            "MATCH (d:Document {source: $source}) "
            "MERGE (ch)-[:BELONGS_TO]->(d)",
            chunk_id=chunk_id,
            preview=text_preview[:300],
            importance=importance,
            source=source,
        )


# ---------------------------------------------------------------------------
# Concept / Keyword extraction (lightweight)
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset([
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "of", "in",
    "to", "for", "with", "on", "at", "by", "from", "as", "into",
    "about", "that", "this", "it", "and", "or", "but", "not", "if",
    "이", "그", "저", "것", "수", "등", "및", "또는", "위해",
    "에서", "으로", "하는", "되는", "있는", "없는", "한",
])


def extract_keywords(text: str, top_k: int = 15) -> list[str]:
    """Simple TF-based keyword extraction."""
    words = re.findall(r"[a-zA-Z가-힣]{2,}", text.lower())
    words = [w for w in words if w not in _STOP_WORDS and len(w) > 1]

    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_k]]


# ---------------------------------------------------------------------------
# Relationship builders by granularity
# ---------------------------------------------------------------------------

def build_word_sentence_relations(
    chunk_id: str,
    text: str,
    source: str,
) -> None:
    """Word-Sentence: link Keyword nodes to the Chunk containing them."""
    driver = get_driver()
    keywords = extract_keywords(text)

    with driver.session() as session:
        for kw in keywords:
            session.run(
                "MERGE (k:Keyword {name: $name}) "
                "WITH k "
                "MATCH (ch:Chunk {chunk_id: $chunk_id}) "
                "MERGE (k)-[:APPEARS_IN]->(ch)",
                name=kw,
                chunk_id=chunk_id,
            )


def build_sentence_sentence_relations(
    chunk_ids: list[str],
) -> None:
    """Sentence-Sentence: link sequential/adjacent chunks with FOLLOWS edges."""
    driver = get_driver()
    with driver.session() as session:
        for i in range(len(chunk_ids) - 1):
            session.run(
                "MATCH (a:Chunk {chunk_id: $id_a}), (b:Chunk {chunk_id: $id_b}) "
                "MERGE (a)-[:FOLLOWS]->(b)",
                id_a=chunk_ids[i],
                id_b=chunk_ids[i + 1],
            )


def build_word_word_relations(
    text: str,
    window_size: int = 5,
) -> None:
    """Word-Word: co-occurrence graph — keywords that appear within a
    sliding window are linked with CO_OCCURS edges."""
    driver = get_driver()
    keywords_set = set(extract_keywords(text, top_k=30))
    words = re.findall(r"[a-zA-Z가-힣]{2,}", text.lower())
    filtered = [w for w in words if w in keywords_set]

    pairs_seen: set[tuple[str, str]] = set()
    with driver.session() as session:
        for i, w1 in enumerate(filtered):
            for w2 in filtered[i + 1: i + 1 + window_size]:
                if w1 == w2:
                    continue
                pair = tuple(sorted([w1, w2]))
                if pair in pairs_seen:
                    continue
                pairs_seen.add(pair)
                session.run(
                    "MERGE (a:Keyword {name: $w1}) "
                    "MERGE (b:Keyword {name: $w2}) "
                    "MERGE (a)-[r:CO_OCCURS]-(b) "
                    "ON CREATE SET r.weight = 1 "
                    "ON MATCH SET r.weight = r.weight + 1",
                    w1=pair[0],
                    w2=pair[1],
                )


# ---------------------------------------------------------------------------
# Concept linking
# ---------------------------------------------------------------------------

def link_concept_to_document(concept: str, source: str, relation: str = "REFERENCED_IN") -> None:
    """Link a high-level Concept node to a Document."""
    driver = get_driver()
    with driver.session() as session:
        session.run(
            f"MERGE (c:Concept {{name: $concept}}) "
            f"WITH c "
            f"MATCH (d:Document {{source: $source}}) "
            f"MERGE (c)-[:{relation}]->(d)",
            concept=concept,
            source=source,
        )


# ---------------------------------------------------------------------------
# Full graph builder
# ---------------------------------------------------------------------------

def build_graph_for_document(
    source: str,
    doc_type: str,
    chunks: list[dict],
    granularity: RelationGranularity = RelationGranularity.WORD_SENTENCE,
) -> dict:
    """Build the full knowledge graph for a preprocessed document.

    Args:
        chunks: list of dicts with keys: chunk_id, text, importance
        granularity: which relationship strategy to use
    """
    init_schema()
    upsert_document(source, doc_type)

    chunk_ids = []
    for chunk in chunks:
        cid = chunk["chunk_id"]
        chunk_ids.append(cid)
        upsert_chunk_node(cid, source, chunk["text"], chunk.get("importance", "unknown"))

        if granularity in (RelationGranularity.WORD_SENTENCE, RelationGranularity.WORD_WORD):
            build_word_sentence_relations(cid, chunk["text"], source)

    if granularity == RelationGranularity.SENTENCE_SENTENCE:
        build_sentence_sentence_relations(chunk_ids)

    if granularity == RelationGranularity.WORD_WORD:
        full_text = "\n".join(c["text"] for c in chunks)
        build_word_word_relations(full_text)

    return {
        "source": source,
        "granularity": granularity.value,
        "nodes_created": len(chunks),
    }


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_related_concepts(concept: str, max_depth: int = 2) -> list[dict]:
    """Find documents and concepts related to a given concept."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            "MATCH path = (c:Concept {name: $concept})-[*1..$depth]-(related) "
            "RETURN labels(related) AS labels, properties(related) AS props "
            "LIMIT 50",
            concept=concept,
            depth=max_depth,
        )
        return [{"labels": r["labels"], "properties": r["props"]} for r in result]


def get_document_graph(source: str) -> dict:
    """Return the subgraph for a single document: its chunks, keywords, concepts."""
    driver = get_driver()
    nodes = []
    edges = []
    with driver.session() as session:
        # Chunks
        result = session.run(
            "MATCH (d:Document {source: $source})<-[:BELONGS_TO]-(ch:Chunk) "
            "RETURN ch.chunk_id AS id, ch.importance AS importance, ch.text_preview AS preview",
            source=source,
        )
        for r in result:
            nodes.append({"id": r["id"], "type": "chunk", "importance": r["importance"]})

        # Keyword links
        result = session.run(
            "MATCH (d:Document {source: $source})<-[:BELONGS_TO]-(ch:Chunk)<-[:APPEARS_IN]-(k:Keyword) "
            "RETURN k.name AS keyword, ch.chunk_id AS chunk_id",
            source=source,
        )
        kw_set = set()
        for r in result:
            kw = r["keyword"]
            if kw not in kw_set:
                nodes.append({"id": kw, "type": "keyword"})
                kw_set.add(kw)
            edges.append({"from": kw, "to": r["chunk_id"], "type": "APPEARS_IN"})

        # Sequential links
        result = session.run(
            "MATCH (d:Document {source: $source})<-[:BELONGS_TO]-(a:Chunk)-[:FOLLOWS]->(b:Chunk) "
            "RETURN a.chunk_id AS from_id, b.chunk_id AS to_id",
            source=source,
        )
        for r in result:
            edges.append({"from": r["from_id"], "to": r["to_id"], "type": "FOLLOWS"})

    return {"nodes": nodes, "edges": edges}
