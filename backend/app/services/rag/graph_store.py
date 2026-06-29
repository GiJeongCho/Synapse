"""Graph DB 추상화(§13).

Neo4j 접근은 ``GraphStore`` 를 통해서만 한다. Cypher 는 본 클래스 내부로 캡슐화한다.
연결 자격증명은 ``.env``, 한도는 ``settings.graph_search_limit``.
"""

from __future__ import annotations

from typing import List, Optional

from app.core.config import settings
from app.core.errors.exceptions import GraphDBConnectionError
from app.core.logging import logger

log = logger(__name__)


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
        """개념-문서-저자 관계를 탐색해 엔티티+관계 목록을 반환한다.

        TODO: 도메인 스키마 확정 후 fulltext 인덱스 기반 Cypher 로 구현.
        """
        _ = (query, limit or settings.graph_search_limit)
        raise NotImplementedError(
            "GraphStore.search 는 그래프 스키마 확정 후 구현 예정(§13)."
        )

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
        """부팅 시 전문 검색 인덱스를 보장한다(§13.3). TODO: 스키마 확정 후 구현."""
        raise NotImplementedError("ensure_fulltext_indexes 미구현(스키마 대기).")

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
