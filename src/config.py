"""Application configuration loaded from environment and sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    """Runtime settings for CampusAsk."""

    project_root: Path = PROJECT_ROOT
    data_raw: Path = PROJECT_ROOT / "data" / "raw"
    data_processed: Path = PROJECT_ROOT / "data" / "processed"
    data_benchmark: Path = PROJECT_ROOT / "data" / "benchmark"
    indexes_dir: Path = PROJECT_ROOT / "indexes"
    results_dir: Path = PROJECT_ROOT / "results"
    sources_registry: Path = PROJECT_ROOT / "data" / "raw" / "sources.json"

    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    evidence_min_score: float = float(os.getenv("EVIDENCE_MIN_SCORE", "0.45"))

    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    faiss_index_path: Path = PROJECT_ROOT / "indexes" / "campusask.faiss"
    metadata_path: Path = PROJECT_ROOT / "indexes" / "chunks.jsonl"

    def ensure_dirs(self) -> None:
        for path in (
            self.data_raw,
            self.data_processed,
            self.data_benchmark,
            self.indexes_dir,
            self.results_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
