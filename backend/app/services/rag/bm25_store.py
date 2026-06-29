"""BM25 키워드 검색 — 청크 텍스트를 인메모리 인덱스로 관리."""
from __future__ import annotations
from rank_bm25 import BM25Okapi


class BM25Store:
    def __init__(self):
        self._corpus: list[str] = []      # 청크 텍스트 목록
        self._ids: list[str] = []          # 청크 ID 목록
        self._bm25 = None

    def build(self, chunks: list[dict]) -> None:
        """Milvus에서 가져온 청크로 인덱스 빌드."""
        self._corpus = [c.get("text", "") for c in chunks]
        self._ids = [c.get("id", "") for c in chunks]
        tokenized = [text.split() for text in self._corpus]
        self._bm25 = BM25Okapi(tokenized)

    def search(self, query: str, top_k: int = 50) -> list[dict]:
        """키워드 검색 결과 반환."""
        if not self._bm25:
            return []
        tokens = query.split()
        scores = self._bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            {"id": self._ids[i], "bm25_score": float(scores[i])}
            for i in top_indices if scores[i] > 0
        ]


bm25_store = BM25Store()