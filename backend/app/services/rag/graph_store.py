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
    ) -> None:
        """Document → Chunk 관계를 Neo4j에 저장."""
        driver = self._get_driver()
        with driver.session() as session:
            session.run(
                """
                MERGE (d:Document {source: $source})
                SET d.doc_type = $doc_type
                """,
                source=source, doc_type=doc_type
            )
            for chunk_id, section in zip(chunk_ids, sections):
                session.run(
                    """
                    MERGE (c:Chunk {id: $chunk_id})
                    SET c.section = $section
                    WITH c
                    MATCH (d:Document {source: $source})
                    MERGE (d)-[:HAS_CHUNK]->(c)
                    """,
                    chunk_id=chunk_id, section=section, source=source
                )
                

    def ensure_fulltext_indexes(self) -> None:
        """부팅 시 전문 검색 인덱스를 보장한다(§13.3). TODO: 스키마 확정 후 구현."""
        raise NotImplementedError("ensure_fulltext_indexes 미구현(스키마 대기).")

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None


graph_store = GraphStore()
