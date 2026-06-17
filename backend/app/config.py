"""Synapse 전역 설정.

모든 설정은 본 모듈의 ``Settings``(pydantic-settings) + ``.env`` 로만 관리한다.
매직 넘버/URL 하드코딩 금지(§21). 에이전트 LLM 설정은 ``<AGENT>_AGENT`` @property 로 추가한다(§8.2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from pydantic_settings import BaseSettings

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # ---- 프로젝트 ----
    project_name: str = "synapse"
    log_level: str = "INFO"
    logging_no_color: bool = False

    # ---- LLM (provider 추상화) ----
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"

    # ---- Embedding ----
    embedding_model: str = "Qwen/Qwen3-Embedding"
    embedding_dim: int = 1024
    embed_api_url: str = "http://ppsystem.kro.kr:5000"
    rerank_api_url: str = "http://ppsystem.kro.kr:5000"

    # ---- Vector DB (Milvus Lite / Qdrant) ----
    milvus_uri: str = str(_BACKEND_ROOT / "synapse.db")
    milvus_collection: str = "synapse_chunks"

    # ---- Graph DB (Neo4j) ----
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # ---- 전처리 / 청킹 (tokens) ----
    chunk_min_tokens: int = 100
    chunk_max_tokens: int = 1100
    chunk_merge_ceiling: int = 1150

    # ---- 스코어링 가중치 ----
    quality_weight: float = 0.4
    importance_weight: float = 0.6

    # ---- RAG 검색 ----
    vector_search_top_k: int = 10
    vector_search_similarity_threshold: float = 0.3
    graph_search_limit: int = 20
    rag_fusion_k: int = 60
    rag_prefetch_limit: int = 50

    # ---- 에이전트 / 워크플로우 ----
    max_iteration: int = 3
    callback_url: str = ""

    # ---- 업로드 ----
    upload_dir: str = str(_BACKEND_ROOT / "uploads")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # ------------------------------------------------------------------
    # 파생 / 조합형 설정 (§21.5)
    # ------------------------------------------------------------------
    @property
    def default_gen_params(self) -> Dict[str, Any]:
        """모든 에이전트가 공유하는 기본 생성 파라미터."""
        return {"temperature": 0.2, "max_tokens": 4096}

    def _agent_cfg(self, model_name: str | None = None) -> Dict[str, Any]:
        """에이전트 LLM 설정 공통 빌더.

        모델/프로바이더 교체는 본 메서드(또는 각 ``<AGENT>_AGENT``)만 수정하면 된다.
        노드 코드는 ``get_llm_for_agent()`` 만 사용하므로 영향이 없다(§8.2).
        """
        return {
            "provider": self.llm_provider,
            "model_name": model_name or self.llm_model,
            "api_key": self.anthropic_api_key,
            "gen_params": self.default_gen_params,
        }

    # agent_name(소문자) ↔ <대문자>_AGENT 가 1:1 로 매핑된다(§3.2).
    @property
    def SUPERVISOR_AGENT(self) -> Dict[str, Any]:
        return self._agent_cfg()

    @property
    def SEARCH_AGENT(self) -> Dict[str, Any]:
        return self._agent_cfg()

    @property
    def CRAWL_AGENT(self) -> Dict[str, Any]:
        return self._agent_cfg()

    @property
    def GRAPH_AGENT(self) -> Dict[str, Any]:
        return self._agent_cfg()

    @property
    def ANALYST_AGENT(self) -> Dict[str, Any]:
        return self._agent_cfg()

    @property
    def WRITER_AGENT(self) -> Dict[str, Any]:
        return self._agent_cfg()


settings = Settings()