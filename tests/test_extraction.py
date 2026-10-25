"""Extraction provenance tests for HTML and PDF fixtures."""

from pathlib import Path

from src.extraction import extract_html, extract_pdf

FIXTURES = Path(__file__).parent / "fixtures"
RAW_FIXTURES = Path(__file__).resolve().parents[1] / "data" / "raw" / "fixtures"


def test_extract_html_sections_and_provenance():
    html = (RAW_FIXTURES / "sample_handbook.html").read_text(encoding="utf-8")
    pages = extract_html(
        html,
        source_id="fixture_policy_handbook",
        title="Sample Handbook",
        url="https://example.invalid/handbook",
        year="2024-2025",
        level="all",
    )
    assert pages
    assert any("Grade Replacement" in (p.section or "") for p in pages)
    joined = " ".join(p.text for p in pages)
    assert "9 credit hours" in joined
    for p in pages:
        assert p.source_id == "fixture_policy_handbook"
        assert p.content_type == "html"
        assert p.page is None
        assert p.url.startswith("https://")


def test_extract_pdf_keeps_page_numbers():
    pages = extract_pdf(
        FIXTURES / "mini.pdf",
        source_id="fixture_pdf",
        title="Mini PDF",
        url="https://example.invalid/mini.pdf",
        year="2024-2025",
        level="undergraduate",
    )
    assert len(pages) >= 1
    assert pages[0].page == 1
    assert pages[0].content_type == "pdf"
    # Text extraction quality varies by PDF producer; page metadata must exist.
    assert pages[0].source_id == "fixture_pdf"
