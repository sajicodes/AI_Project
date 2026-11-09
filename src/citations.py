"""Citation validation against retrieved chunk IDs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.retrieval import RetrievedPassage, is_dev_fixture

CITATION_PATTERN = re.compile(r"\[cite:([^\]]+)\]", re.IGNORECASE)


@dataclass
class CitationCheckResult:
    valid_ids: list[str]
    invalid_ids: list[str]
    cleaned_answer: str
    all_valid: bool


def extract_citation_ids(text: str) -> list[str]:
    return [m.group(1).strip() for m in CITATION_PATTERN.finditer(text or "")]


def strip_citation_markers(text: str) -> str:
    """Remove all [cite:…] markers from visible answer text."""
    cleaned = CITATION_PATTERN.sub("", text or "")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r" +\.", ".", cleaned)
    return cleaned.strip()


def validate_citations(
    answer: str,
    passages: list[RetrievedPassage],
) -> CitationCheckResult:
    """Validate [cite:ID] against retrieved chunks; strip markers from visible text."""
    allowed = {p.chunk_id for p in passages}
    found = extract_citation_ids(answer)
    valid: list[str] = []
    invalid: list[str] = []
    for cid in found:
        if cid in allowed:
            if cid not in valid:
                valid.append(cid)
        else:
            if cid not in invalid:
                invalid.append(cid)

    cleaned = strip_citation_markers(answer or "")

    return CitationCheckResult(
        valid_ids=valid,
        invalid_ids=invalid,
        cleaned_answer=cleaned,
        all_valid=len(invalid) == 0,
    )


def format_source_block(passages: list[RetrievedPassage], cited_ids: list[str] | None = None) -> list[dict]:
    """Build UI-friendly source cards; prefer cited IDs, else all retrieved.

    Development fixtures are never shown as production sources.
    """
    by_id = {p.chunk_id: p for p in passages if not is_dev_fixture(p.chunk)}
    order = cited_ids if cited_ids else [p.chunk_id for p in passages]
    seen: set[str] = set()
    out: list[dict] = []
    for cid in order:
        if cid in seen or cid not in by_id:
            continue
        seen.add(cid)
        p = by_id[cid]
        out.append(
            {
                "chunk_id": p.chunk_id,
                "title": p.chunk.title,
                "url": p.chunk.url,
                "location": p.location_label(),
                "page": p.chunk.page,
                "section": p.chunk.section,
                "year": p.chunk.year,
                "level": p.chunk.level,
                "score": round(p.score, 4),
                "excerpt": p.chunk.text[:400] + ("…" if len(p.chunk.text) > 400 else ""),
            }
        )
    return out
