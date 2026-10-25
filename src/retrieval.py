"""Query embedding and top-k retrieval with optional level/year filters."""

from __future__ import annotations

from dataclasses import dataclass

from src.chunking import Chunk
from src.config import Settings, get_settings
from src.embeddings import embed_query
from src.vector_store import VectorStore, load_store


@dataclass
class RetrievedPassage:
    chunk: Chunk
    score: float

    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id

    def location_label(self) -> str:
        if self.chunk.content_type == "pdf" and self.chunk.page is not None:
            return f"PDF page {self.chunk.page}"
        if self.chunk.section:
            return f"Section: {self.chunk.section}"
        return "Location unavailable"


def retrieve(
    query: str,
    store: VectorStore,
    *,
    settings: Settings | None = None,
    top_k: int | None = None,
    level: str | None = None,
    year: str | None = None,
) -> list[RetrievedPassage]:
    settings = settings or get_settings()
    k = top_k if top_k is not None else settings.top_k
    vector = embed_query(query, model_name=settings.embedding_model)
    hits = store.search(vector, top_k=k, level=level, year=year)
    return [RetrievedPassage(chunk=c, score=s) for c, s in hits]


def load_default_store(settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()
    return load_store(settings.faiss_index_path, settings.metadata_path)
