"""Query embedding and top-k retrieval with optional level/year filters."""

from __future__ import annotations

from dataclasses import dataclass

from src.chunking import Chunk
from src.config import Settings, get_settings
from src.embeddings import embed_query
from src.query_expand import expand_query, infer_level_hint, lexical_terms
from src.vector_store import VectorStore, load_store

# Soft lexical boost when catalog phrasing matches expanded policy terms.
_LEXICAL_BONUS = 0.06
_LEXICAL_BONUS_CAP = 0.12


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


def _apply_lexical_boost(
    hits: list[tuple[Chunk, float]],
    terms: list[str],
) -> list[tuple[Chunk, float]]:
    if not terms:
        return hits
    boosted: list[tuple[Chunk, float]] = []
    for chunk, score in hits:
        text = (chunk.text or "").lower()
        bonus = 0.0
        for term in terms:
            if term.lower() in text:
                bonus += _LEXICAL_BONUS
        if bonus:
            bonus = min(bonus, _LEXICAL_BONUS_CAP)
        boosted.append((chunk, float(score) + bonus))
    boosted.sort(key=lambda item: item[1], reverse=True)
    return boosted


def _merge_hits(
    buckets: list[list[tuple[Chunk, float]]],
) -> list[tuple[Chunk, float]]:
    """Keep the max score per chunk_id across query variants."""
    best: dict[str, tuple[Chunk, float]] = {}
    for hits in buckets:
        for chunk, score in hits:
            prev = best.get(chunk.chunk_id)
            if prev is None or score > prev[1]:
                best[chunk.chunk_id] = (chunk, score)
    merged = list(best.values())
    merged.sort(key=lambda item: item[1], reverse=True)
    return merged


def retrieve(
    query: str,
    store: VectorStore,
    *,
    settings: Settings | None = None,
    top_k: int | None = None,
    level: str | None = None,
    year: str | None = None,
    expand: bool = True,
) -> list[RetrievedPassage]:
    """Retrieve top-k passages with optional query expansion and soft level hints."""
    settings = settings or get_settings()
    k = top_k if top_k is not None else settings.top_k
    if not (query or "").strip():
        return []

    variants = expand_query(query) if expand else [query.strip()]
    terms = lexical_terms(query)

    # When the UI filter is "all"/None, prefer a level implied by the question.
    effective_level = level
    if not effective_level or effective_level.lower() in {"all", ""}:
        hint = infer_level_hint(query)
        if hint:
            effective_level = hint

    # Over-fetch per variant so fusion + lexical boost can re-rank.
    fetch_k = max(k * 3, k)
    buckets: list[list[tuple[Chunk, float]]] = []
    for variant in variants:
        vector = embed_query(variant, model_name=settings.embedding_model)
        hits = store.search(vector, top_k=fetch_k, level=effective_level, year=year)
        buckets.append(hits)

    # If a hard level filter left results thin or weak, retry without level
    # (catalog metadata is imperfect; prefer answering from the right pages).
    merged = _merge_hits(buckets)
    max_score = max((s for _, s in merged), default=0.0)
    weak = max_score < settings.evidence_min_score
    thin = len(merged) < max(2, k // 2)
    if effective_level and (thin or weak):
        retry_buckets: list[list[tuple[Chunk, float]]] = []
        for variant in variants:
            vector = embed_query(variant, model_name=settings.embedding_model)
            retry_buckets.append(
                store.search(vector, top_k=fetch_k, level=None, year=year)
            )
        merged = _merge_hits(retry_buckets)

    merged = _apply_lexical_boost(merged, terms)[:k]
    return [RetrievedPassage(chunk=c, score=s) for c, s in merged]


def load_default_store(settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()
    return load_store(settings.faiss_index_path, settings.metadata_path)
