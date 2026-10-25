"""Token-approximate chunking that preserves provenance metadata."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any

from src.extraction import ExtractedPage


def approx_token_count(text: str) -> int:
    """Approximate tokens as whitespace-separated words (good enough for sizing)."""
    return len(re.findall(r"\S+", text))


def _stable_chunk_id(source_id: str, page: int | None, section: str | None, ordinal: int, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    loc = f"p{page}" if page is not None else f"s{(section or 'body')[:40]}"
    return f"{source_id}::{loc}::{ordinal}::{digest}"


@dataclass
class Chunk:
    """A retrieval unit with full provenance."""

    chunk_id: str
    text: str
    source_id: str
    title: str
    url: str
    year: str
    level: str
    content_type: str
    page: int | None
    section: str | None
    token_estimate: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        return cls(**{k: data[k] for k in cls.__dataclass_fields__})


def chunk_page(
    page: ExtractedPage,
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Chunk]:
    """Split one extracted page into overlapping chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    text = (page.text or "").strip()
    if not text:
        return []

    words = re.findall(r"\S+", text)
    if not words:
        return []

    step = max(1, chunk_size - chunk_overlap)
    chunks: list[Chunk] = []
    ordinal = 0
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size]
        if not window:
            break
        piece = " ".join(window)
        ordinal += 1
        chunks.append(
            Chunk(
                chunk_id=_stable_chunk_id(
                    page.source_id, page.page, page.section, ordinal, piece
                ),
                text=piece,
                source_id=page.source_id,
                title=page.title,
                url=page.url,
                year=page.year,
                level=page.level,
                content_type=page.content_type,
                page=page.page,
                section=page.section,
                token_estimate=len(window),
            )
        )
        if start + chunk_size >= len(words):
            break
    return chunks


def chunk_pages(
    pages: list[ExtractedPage],
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Chunk]:
    out: list[Chunk] = []
    for page in pages:
        out.extend(chunk_page(page, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    return out
