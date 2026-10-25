#!/usr/bin/env python3
"""Ingest allowlisted sources, chunk, embed, and persist FAISS + metadata."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chunking import chunk_pages
from src.config import get_settings
from src.embeddings import embed_texts
from src.ingestion import ingest_all, write_processed_pages
from src.vector_store import build_index, save_store

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("build_index")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CampusAsk FAISS index")
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Path to sources.json (default: data/raw/sources.json)",
    )
    args = parser.parse_args()
    settings = get_settings()
    registry = args.registry or settings.sources_registry

    pages, log = ingest_all(registry, settings.data_raw)
    usable = [p for p in pages if p.text.strip()]
    logger.info(
        "Ingested %d pages (%d with text) from %s",
        len(pages),
        len(usable),
        registry,
    )

    processed = settings.data_processed / "pages.jsonl"
    write_processed_pages(usable, processed)
    (settings.data_processed / "ingest_log.json").write_text(
        json.dumps(log, indent=2), encoding="utf-8"
    )

    chunks = chunk_pages(
        usable,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    if not chunks:
        logger.error("No chunks produced. Check sources and extraction logs.")
        return 1

    logger.info("Embedding %d chunks with %s", len(chunks), settings.embedding_model)
    vectors = embed_texts([c.text for c in chunks], model_name=settings.embedding_model)
    store = build_index(vectors, chunks)
    save_store(store, settings.faiss_index_path, settings.metadata_path)

    meta = {
        "n_pages": len(usable),
        "n_chunks": len(chunks),
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "embedding_model": settings.embedding_model,
        "index_path": str(settings.faiss_index_path),
        "metadata_path": str(settings.metadata_path),
    }
    (settings.indexes_dir / "build_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    logger.info("Index build complete: %s", meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
