"""Tests for chunking and provenance retention."""

from src.chunking import approx_token_count, chunk_page, chunk_pages
from src.extraction import ExtractedPage


def _page(text: str, **kwargs) -> ExtractedPage:
    base = dict(
        source_id="fixture_ug_catalog",
        title="Sample UG",
        url="https://example.invalid/ug",
        year="2024-2025",
        level="undergraduate",
        content_type="html",
        page=None,
        section="Minor Requirements",
        text=text,
        extraction_notes=[],
    )
    base.update(kwargs)
    return ExtractedPage(**base)


def test_approx_token_count():
    assert approx_token_count("one two three") == 3


def test_chunk_page_preserves_provenance():
    words = " ".join(f"word{i}" for i in range(120))
    chunks = chunk_page(_page(words), chunk_size=40, chunk_overlap=10)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.source_id == "fixture_ug_catalog"
        assert c.section == "Minor Requirements"
        assert c.level == "undergraduate"
        assert c.chunk_id.startswith("fixture_ug_catalog::")
        assert c.token_estimate <= 40


def test_empty_page_yields_no_chunks():
    assert chunk_page(_page("")) == []
    assert chunk_pages([_page("")]) == []


def test_overlap_constraint():
    try:
        chunk_page(_page("a b c"), chunk_size=10, chunk_overlap=10)
        assert False, "expected ValueError"
    except ValueError:
        pass
