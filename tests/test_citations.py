"""Citation validation must reject invented IDs."""

from src.chunking import Chunk
from src.citations import extract_citation_ids, validate_citations
from src.retrieval import RetrievedPassage


def _passage(cid: str) -> RetrievedPassage:
    chunk = Chunk(
        chunk_id=cid,
        text="Sample policy text about grade replacement.",
        source_id="fixture_policy_handbook",
        title="Sample Handbook",
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


def test_validate_rejects_unknown_ids():
    passages = [_passage("real-1")]
    answer = "Students may replace a D [cite:real-1] or invent [cite:fake-99]."
    result = validate_citations(answer, passages)
    assert result.valid_ids == ["real-1"]
    assert result.invalid_ids == ["fake-99"]
    assert not result.all_valid
    assert "[cite:fake-99]" not in result.cleaned_answer
    assert "[cite:real-1]" in result.cleaned_answer
