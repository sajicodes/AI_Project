"""Citation validation must reject invented IDs and strip markers from answers."""

from src.chunking import Chunk
from src.citations import extract_citation_ids, strip_citation_markers, validate_citations
from src.retrieval import RetrievedPassage


def _passage(cid: str, *, title: str = "Sample Handbook", source_id: str = "ucm_ug_catalog") -> RetrievedPassage:
    chunk = Chunk(
        chunk_id=cid,
        text="Sample policy text about grade replacement.",
        source_id=source_id,
        title=title,
        url="https://example.invalid/handbook",
        year="2024-2025",
        level="all",
        content_type="html",
        page=None,
        section="Grade Replacement",
        token_estimate=8,
    )
    return RetrievedPassage(chunk=chunk, score=0.55)


def test_extract_citation_ids():
    text = "Rule A [cite:abc] and rule B [cite:def]."
    assert extract_citation_ids(text) == ["abc", "def"]


def test_strip_citation_markers():
    text = "Students may replace a D [cite:real-1] under catalog rules."
    cleaned = strip_citation_markers(text)
    assert "[cite:" not in cleaned
    assert "real-1" not in cleaned
    assert "Students may replace a D" in cleaned
    assert "under catalog rules" in cleaned


def test_validate_rejects_unknown_ids_and_strips_all_markers():
    passages = [_passage("real-1")]
    answer = "Students may replace a D [cite:real-1] or invent [cite:fake-99]."
    result = validate_citations(answer, passages)
    assert result.valid_ids == ["real-1"]
    assert result.invalid_ids == ["fake-99"]
    assert not result.all_valid
    assert "[cite:" not in result.cleaned_answer
    assert "fake-99" not in result.cleaned_answer
    assert "real-1" not in result.cleaned_answer
    assert "Students may replace a D" in result.cleaned_answer


def test_format_source_block_excludes_dev_fixtures():
    from src.citations import format_source_block

    real = _passage("real-1", title="UCM Graduate Catalog 2026-2027", source_id="ucm_grad_catalog_2026_2027")
    fixture = _passage(
        "fix-1",
        title="[DEV FIXTURE] Sample Graduate Catalog Excerpt",
        source_id="fixture_grad_catalog",
    )
    cards = format_source_block([real, fixture], cited_ids=["real-1", "fix-1"])
    assert len(cards) == 1
    assert cards[0]["chunk_id"] == "real-1"
