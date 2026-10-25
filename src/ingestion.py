"""Allowlist-driven document ingestion with provenance logging."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.extraction import ExtractedPage, extract_html, extract_pdf, fetch_html

logger = logging.getLogger(__name__)


@dataclass
class SourceRecord:
    """One allowlisted official source."""

    source_id: str
    title: str
    url: str
    year: str
    level: str
    content_type: str  # pdf | html
    local_path: str | None = None
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceRecord:
        return cls(
            source_id=data["source_id"],
            title=data["title"],
            url=data["url"],
            year=str(data.get("year", "unknown")),
            level=str(data.get("level", "all")).lower(),
            content_type=str(data["content_type"]).lower(),
            local_path=data.get("local_path"),
            enabled=bool(data.get("enabled", True)),
        )


def load_sources_registry(path: Path) -> list[SourceRecord]:
    if not path.exists():
        raise FileNotFoundError(
            f"Sources registry not found: {path}. "
            "Create data/raw/sources.json with allowlisted UCM documents."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    sources = [SourceRecord.from_dict(item) for item in raw.get("sources", [])]
    return [s for s in sources if s.enabled]


def ingest_source(source: SourceRecord, raw_dir: Path) -> list[ExtractedPage]:
    """Ingest one allowlisted source from local file or URL."""
    if source.content_type == "pdf":
        if not source.local_path:
            raise ValueError(f"PDF source {source.source_id} requires local_path")
        path = Path(source.local_path)
        if not path.is_absolute():
            path = raw_dir / path
        if not path.exists():
            logger.error("Missing PDF for %s at %s", source.source_id, path)
            return [
                ExtractedPage(
                    source_id=source.source_id,
                    title=source.title,
                    url=source.url,
                    year=source.year,
                    level=source.level,
                    content_type="pdf",
                    page=None,
                    section=None,
                    text="",
                    extraction_notes=[f"missing_local_file: {path}"],
                )
            ]
        return extract_pdf(
            path,
            source_id=source.source_id,
            title=source.title,
            url=source.url,
            year=source.year,
            level=source.level,
        )

    if source.content_type == "html":
        local: Path | None = None
        if source.local_path:
            local = Path(source.local_path)
            if not local.is_absolute():
                local = raw_dir / local
        if local and local.exists():
            html = local.read_text(encoding="utf-8", errors="replace")
        else:
            html = fetch_html(source.url)
            # Cache a copy for reproducibility when network is available.
            cache = raw_dir / "html_cache" / f"{source.source_id}.html"
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(html, encoding="utf-8")
        return extract_html(
            html,
            source_id=source.source_id,
            title=source.title,
            url=source.url,
            year=source.year,
            level=source.level,
            )

    raise ValueError(f"Unknown content_type for {source.source_id}: {source.content_type}")


def ingest_all(registry_path: Path, raw_dir: Path) -> tuple[list[ExtractedPage], dict[str, Any]]:
    """Ingest every enabled allowlisted source; return pages + provenance log."""
    sources = load_sources_registry(registry_path)
    all_pages: list[ExtractedPage] = []
    log: dict[str, Any] = {"sources": [], "total_pages": 0, "empty_pages": 0}

    for source in sources:
        try:
            pages = ingest_source(source, raw_dir)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingest failed for %s", source.source_id)
            entry = {
                "source_id": source.source_id,
                "status": "error",
                "error": str(exc),
                "pages": 0,
            }
            log["sources"].append(entry)
            continue

        empty = sum(1 for p in pages if not p.text.strip())
        notes = [n for p in pages for n in p.extraction_notes]
        entry = {
            "source_id": source.source_id,
            "status": "ok" if pages and empty < len(pages) else "degraded",
            "pages": len(pages),
            "empty_pages": empty,
            "notes": notes[:50],
        }
        log["sources"].append(entry)
        log["total_pages"] += len(pages)
        log["empty_pages"] += empty
        all_pages.extend(pages)

    return all_pages, log


def write_processed_pages(pages: list[ExtractedPage], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for page in pages:
            fh.write(json.dumps(page.to_dict(), ensure_ascii=False) + "\n")
