"""Graph DB 추상화(§13).

Neo4j 접근은 ``GraphStore`` 를 통해서만 한다. Cypher 는 본 클래스 내부로 캡슐화한다.
연결 자격증명은 ``.env``, 한도는 ``settings.graph_search_limit``.
"""

from __future__ import annotations

from typing import List, Optional

import re

from app.core.config import settings
from app.core.errors.exceptions import GraphDBConnectionError
from app.core.logging import logger

log = logger(__name__)

_ARTICLE_NO_QUERY_RE = re.compile(r'제\s*(\d+)\s*조')


class GraphStore:
    """Neo4j(bolt) 관계 탐색 래퍼. 드라이버는 지연 생성한다."""

    def __init__(self) -> None:
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            try:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
            except Exception as exc:  # noqa: BLE001
                log.error("[GraphStore] 연결 실패: %s", exc, exc_info=True)
                raise GraphDBConnectionError(details={"cause": str(exc)})
        return self._driver

    async def search(self, query: str, limit: Optional[int] = None) -> List[dict]:
        """조문 번호 직접 조회 또는 Article fulltext 검색."""
        lim = limit or settings.graph_search_limit
        results: list[dict] = []

        try:
            driver = self._get_driver()
        except Exception:
            return []

        # 1. 쿼리에 조문 번호 패턴이 있으면 Article 노드 직접 조회
        m = _ARTICLE_NO_QUERY_RE.search(query)
        if m:
            article_no = f"제{m.group(1)}조"
            with driver.session() as session:
                records = session.run(
                    """
                    MATCH (a:Article {article_no: $article_no})-[:HAS_CHUNK]->(c:Chunk)
                    RETURN c.id AS chunk_id, a.source AS source,
                           a.article_no AS article_no, a.title AS title
                    LIMIT $limit
                    """,
                    article_no=article_no, limit=lim,
                )
                for r in records:
                    results.append({
                        "id": r["chunk_id"],
                        "graph_score": 1.0,
                        "source": r["source"],
                        "article_no": r["article_no"],
                        "title": r["title"],
                    })
            return results

        # 2. 조문 번호 없으면 fulltext 인덱스로 Article 제목 검색
        try:
            with driver.session() as session:
                records = session.run(
                    """
                    CALL db.index.fulltext.queryNodes("articleSearch", $query)
                    YIELD node AS a, score
                    MATCH (a)-[:HAS_CHUNK]->(c:Chunk)
                    RETURN c.id AS chunk_id, a.source AS source,
                           a.article_no AS article_no, a.title AS title, score
                    LIMIT $limit
                    """,
                    query=query, limit=lim,
                )
                for r in records:
                    results.append({
                        "id": r["chunk_id"],
                        "graph_score": float(r["score"]),
                        "source": r["source"],
                        "article_no": r["article_no"],
                        "title": r["title"],
                    })
        except Exception as e:
            log.warning("[GraphStore] fulltext 검색 실패: %s", e)

        return results

    def upsert_document_chunks(
        self,
        source: str,
        doc_type: str,
        chunk_ids: list[str],
        sections: list[str],
        article_map: list[dict],
    ) -> None:
        """Document → Chunk (HAS_CHUNK), Chunk → Chunk (NEXT_CHUNK) 관계를 Neo4j에 저장."""
        driver = self._get_driver()
        with driver.session() as session:
            # 1. Document 노드 생성/갱신
            session.run(
                """
                MERGE (d:Document {source: $source})
                SET d.doc_type = $doc_type
                """,
                source=source, doc_type=doc_type
            )

            # 2. Chunk 노드 생성 + HAS_CHUNK 관계
            for chunk_id, section in zip(chunk_ids, sections):
                session.run(
                    """
                    MERGE (c:Chunk {id: $chunk_id})
                    SET c.section = $section, c.source = $source
                    WITH c
                    MATCH (d:Document {source: $source})
                    MERGE (d)-[:HAS_CHUNK]->(c)
                    """,
                    chunk_id=chunk_id, section=section, source=source
                )

            # 3. NEXT_CHUNK 관계 (청크 순서 연결)
            for i in range(len(chunk_ids) - 1):
                session.run(
                    """
                    MATCH (a:Chunk {id: $current_id})
                    MATCH (b:Chunk {id: $next_id})
                    MERGE (a)-[:NEXT_CHUNK]->(b)
                    """,
                    current_id=chunk_ids[i],
                    next_id=chunk_ids[i + 1]
                )

            # 4. Article 노드 생성 + HAS_ARTICLE, HAS_CHUNK 관계 (법률 문서 전용)
            prev_article_no = None
            for entry in article_map:
                article_no = entry.get("article_no")
                if not article_no:
                    continue
                session.run(
                    """
                    MERGE (a:Article {source: $source, article_no: $article_no})
                    SET a.title = $title
                    WITH a
                    MATCH (d:Document {source: $source})
                    MERGE (d)-[:HAS_ARTICLE]->(a)
                    WITH a
                    MATCH (c:Chunk {id: $chunk_id})
                    MERGE (a)-[:HAS_CHUNK]->(c)
                    """,
                    source=source,
                    article_no=article_no,
                    title=entry.get("title") or "",
                    chunk_id=entry["chunk_id"],
                )
                if prev_article_no:
                    session.run(
                        """
                        MATCH (a1:Article {source: $source, article_no: $prev})
                        MATCH (a2:Article {source: $source, article_no: $curr})
                        MERGE (a1)-[:NEXT_ARTICLE]->(a2)
                        """,
                        source=source,
                        prev=prev_article_no,
                        curr=article_no,
                    )
                prev_article_no = article_no

    def ensure_fulltext_indexes(self) -> None:
        """Article 전문 검색 인덱스를 생성한다 (서버 시작 시 호출)."""
        try:
            driver = self._get_driver()
            with driver.session() as session:
                session.run(
                    """
                    CREATE FULLTEXT INDEX articleSearch IF NOT EXISTS
                    FOR (a:Article) ON EACH [a.title, a.article_no]
                    """
                )
            log.info("[GraphStore] fulltext 인덱스 확인 완료")
        except Exception as e:
            log.warning("[GraphStore] fulltext 인덱스 생성 실패: %s", e)

    def delete_all(self) -> None:
        """Neo4j 전체 노드 및 관계 삭제."""
        driver = self._get_driver()
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def delete_document_and_chunks(self, source: str) -> None:
        driver = self._get_driver()
        with driver.session() as session:
            session.run(
                "MATCH (d:Document {source: $source}) DETACH DELETE d",
                source=source
            )
            session.run(
                "MATCH (c:Chunk {source: $source}) DETACH DELETE c",
                source=source
            )
            session.run(
                "MATCH (a:Article {source: $source}) DETACH DELETE a",
                source=source
            )
            

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None


graph_store = GraphStore()
