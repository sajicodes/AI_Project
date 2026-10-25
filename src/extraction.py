"""PDF and HTML text extraction with provenance metadata."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    """One page (PDF) or section (HTML) of extracted text."""

    source_id: str
    title: str
    url: str
    year: str
    level: str  # undergraduate | graduate | all | unknown
    content_type: str  # pdf | html
    page: int | None
    section: str | None
    text: str
    extraction_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(
    path: Path,
    *,
    source_id: str,
    title: str,
    url: str,
    year: str,
    level: str,
) -> list[ExtractedPage]:
    """Extract text from a PDF, one ExtractedPage per PDF page."""
    pages: list[ExtractedPage] = []
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001 — surface extraction failure as notes
        logger.exception("Failed to open PDF %s", path)
        return [
            ExtractedPage(
                source_id=source_id,
                title=title,
                url=url,
                year=year,
                level=level,
                content_type="pdf",
                page=None,
                section=None,
                text="",
                extraction_notes=[f"pdf_open_failed: {exc}"],
            )
        ]

    for i, page in enumerate(reader.pages, start=1):
        notes: list[str] = []
        try:
            raw = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            raw = ""
            notes.append(f"page_extract_failed: {exc}")

        text = _clean_text(raw)
        if not text:
            notes.append("empty_or_image_only_page")

        pages.append(
            ExtractedPage(
                source_id=source_id,
                title=title,
                url=url,
                year=year,
                level=level,
                content_type="pdf",
                page=i,
                section=None,
                text=text,
                extraction_notes=notes,
            )
        )
    return pages


def _heading_text(tag: Any) -> str:
    return _clean_text(tag.get_text(" ", strip=True))


def extract_html(
    html: str,
    *,
    source_id: str,
    title: str,
    url: str,
    year: str,
    level: str,
) -> list[ExtractedPage]:
    """Extract HTML into section-level pages keyed by heading when possible."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    sections: list[ExtractedPage] = []
    current_heading = title
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current_heading
        text = _clean_text("\n".join(buffer))
        buffer = []
        if not text:
            return
        sections.append(
            ExtractedPage(
                source_id=source_id,
                title=title,
                url=url,
                year=year,
                level=level,
                content_type="html",
                page=None,
                section=current_heading,
                text=text,
                extraction_notes=[],
            )
        )

    headings = main.find_all(re.compile(r"^h[1-3]$", re.I)) if main else []
    if not headings:
        text = _clean_text(main.get_text("\n", strip=True) if main else "")
        notes = [] if text else ["empty_html_body"]
        return [
            ExtractedPage(
                source_id=source_id,
                title=title,
                url=url,
                year=year,
                level=level,
                content_type="html",
                page=None,
                section=title,
                text=text,
                extraction_notes=notes,
            )
        ]

    # Walk document order: accumulate text under each heading.
    for element in main.descendants:
        if getattr(element, "name", None) and re.match(r"^h[1-3]$", element.name, re.I):
            flush()
            current_heading = _heading_text(element) or current_heading
        elif getattr(element, "name", None) in {"p", "li", "td", "th", "dd", "dt"}:
            piece = _clean_text(element.get_text(" ", strip=True))
            if piece:
                buffer.append(piece)

    flush()
    if not sections:
        text = _clean_text(main.get_text("\n", strip=True))
        sections.append(
            ExtractedPage(
                source_id=source_id,
                title=title,
                url=url,
                year=year,
                level=level,
                content_type="html",
                page=None,
                section=title,
                text=text,
                extraction_notes=[] if text else ["empty_html_body"],
            )
        )
    return sections


def fetch_html(url: str, timeout: int = 30) -> str:
    """Download HTML from an allowlisted URL."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {url}")
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "CampusAsk/1.0 (academic research; contact via GitHub)"},
    )
    response.raise_for_status()
    return response.text
