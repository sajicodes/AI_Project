"""Persistent FAISS index and chunk metadata map."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from src.chunking import Chunk

logger = logging.getLogger(__name__)


@dataclass
class VectorStore:
    index: faiss.Index
    chunks: list[Chunk]

    @property
    def size(self) -> int:
        return len(self.chunks)

    def search(
        self,
        query_vector: np.ndarray,
        *,
        top_k: int = 5,
        level: str | None = None,
        year: str | None = None,
    ) -> list[tuple[Chunk, float]]:
        """Return top-k chunks with cosine similarity scores (inner product on normalized vectors)."""
        if self.size == 0:
            return []
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        query_vector = np.asarray(query_vector, dtype=np.float32)

        # Over-fetch when filtering by level/year.
        fetch_k = min(self.size, max(top_k * 5, top_k) if (level or year) else top_k)
        scores, indices = self.index.search(query_vector, fetch_k)
        hits: list[tuple[Chunk, float]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            chunk = self.chunks[idx]
            if level and level.lower() not in {"all", ""}:
                chunk_level = (chunk.level or "all").lower()
                if chunk_level not in {level.lower(), "all", "unknown"}:
                    continue
            if year and year.lower() not in {"all", "", "unknown"}:
                if (chunk.year or "").lower() != year.lower():
                    continue
            hits.append((chunk, float(score)))
            if len(hits) >= top_k:
                break
        return hits


def build_index(vectors: np.ndarray, chunks: list[Chunk]) -> VectorStore:
    if len(chunks) != len(vectors):
        raise ValueError("vectors and chunks length mismatch")
    if len(chunks) == 0:
        dim = 384
        index = faiss.IndexFlatIP(dim)
        return VectorStore(index=index, chunks=[])

    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim != 2:
        raise ValueError("vectors must be 2-D")
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return VectorStore(index=index, chunks=list(chunks))


def save_store(store: VectorStore, index_path: Path, metadata_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(store.index, str(index_path))
    with metadata_path.open("w", encoding="utf-8") as fh:
        for chunk in store.chunks:
            fh.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
    logger.info("Saved FAISS index (%d vectors) to %s", store.size, index_path)


def load_store(index_path: Path, metadata_path: Path) -> VectorStore:
    if not index_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Index not found. Expected {index_path} and {metadata_path}. "
            "Run: python scripts/build_index.py"
        )
    index = faiss.read_index(str(index_path))
    chunks: list[Chunk] = []
    with metadata_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            chunks.append(Chunk.from_dict(json.loads(line)))
    if index.ntotal != len(chunks):
        raise ValueError(
            f"Index/metadata mismatch: {index.ntotal} vectors vs {len(chunks)} chunks"
        )
    return VectorStore(index=index, chunks=chunks)
