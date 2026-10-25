"""Sentence-Transformers embedding helper."""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@lru_cache(maxsize=2)
def load_embedding_model(model_name: str) -> SentenceTransformer:
    logger.info("Loading embedding model: %s", model_name)
    return SentenceTransformer(model_name)


def embed_texts(
    texts: list[str],
    *,
    model_name: str,
    batch_size: int = 32,
    normalize: bool = True,
) -> np.ndarray:
    """Embed texts into a float32 matrix of shape (n, dim)."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    model = load_embedding_model(model_name)
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 64,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    )
    return np.asarray(vectors, dtype=np.float32)


def embed_query(query: str, *, model_name: str) -> np.ndarray:
    vectors = embed_texts([query], model_name=model_name)
    return vectors[0]
