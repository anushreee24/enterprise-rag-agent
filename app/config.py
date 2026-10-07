"""Central configuration. Everything is read from environment variables so the
same code runs on a laptop, in Docker, or in the cloud (12-factor style)."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    embedding_backend: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    min_score: float
    jwt_secret: str
    jwt_minutes: int
    llm_model: str
    anthropic_key: str | None


def load_settings() -> Settings:
    e = os.environ.get
    return Settings(
        data_dir=Path(e("DATA_DIR", "./data")),
        embedding_backend=e("EMBEDDING_BACKEND", "st"),
        embedding_model=e("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        chunk_size=int(e("CHUNK_SIZE", "900")),
        chunk_overlap=int(e("CHUNK_OVERLAP", "150")),
        top_k=int(e("TOP_K", "5")),
        min_score=float(e("MIN_SCORE", "0.15")),
        jwt_secret=e("JWT_SECRET", "dev-secret-change-me"),
        jwt_minutes=int(e("JWT_MINUTES", "60")),
        llm_model=e("LLM_MODEL", "claude-sonnet-5-5"),
        anthropic_key=e("ANTHROPIC_API_KEY") or None,
    )
