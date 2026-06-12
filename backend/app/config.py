from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    project_name: str = "ResearchMind"

    # LLM
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Milvus
    milvus_uri: str = str(Path(__file__).resolve().parent.parent / "synapse.db")
    milvus_collection: str = "research_chunks"

    # Chunk size bounds (tokens)
    chunk_min_tokens: int = 100
    chunk_max_tokens: int = 1100
    chunk_merge_ceiling: int = 1150

    # Scoring weights
    quality_weight: float = 0.4
    importance_weight: float = 0.6

    # Neo4j (Phase 2)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # Upload dir
    upload_dir: str = str(Path(__file__).resolve().parent.parent / "uploads")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
