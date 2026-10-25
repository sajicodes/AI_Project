"""FAISS index round-trip and filtered search."""

import numpy as np

from src.chunking import Chunk
from src.vector_store import build_index, load_store, save_store


def _chunk(cid: str, level: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=cid,
        text=text,
        source_id="fixture_ug_catalog" if level == "undergraduate" else "fixture_grad_catalog",
        title="Fixture",
        url="https://example.invalid/x",
        year="2024-2025",
        level=level,
        content_type="html",
        page=None,
        section="Section",
        token_estimate=5,
    )


def test_index_round_trip(tmp_path):
    chunks = [
        _chunk("a", "undergraduate", "undergraduate credit overload eighteen hours"),
        _chunk("b", "graduate", "graduate full-time enrollment nine hours"),
    ]
    # Simple orthogonal-ish vectors
    vectors = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    store = build_index(vectors, chunks)
    index_path = tmp_path / "t.faiss"
    meta_path = tmp_path / "t.jsonl"
    save_store(store, index_path, meta_path)
    loaded = load_store(index_path, meta_path)
    assert loaded.size == 2

    hits = loaded.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=1)
    assert hits[0][0].chunk_id == "a"

    grad_hits = loaded.search(
        np.array([1.0, 1.0, 0.0], dtype=np.float32),
        top_k=2,
        level="graduate",
    )
    assert all(h[0].level == "graduate" for h in grad_hits)
    assert grad_hits[0][0].chunk_id == "b"
