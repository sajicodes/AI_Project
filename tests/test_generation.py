"""Evidence gate and abstention behavior (no live LLM required)."""

from src.chunking import Chunk
from src.generation import ABSTAIN_MESSAGE, evidence_is_sufficient, generate_answer
from src.retrieval import RetrievedPassage


def _passage(score: float, cid: str = "c1") -> RetrievedPassage:
    chunk = Chunk(
        chunk_id=cid,
        text="Unrelated gardening advice about watering tomatoes twice a week.",
        source_id="fixture_policy_handbook",
        title="Sample Handbook",
        url="https://example.invalid/handbook",
        year="2024-2025",
        level="all",
        content_type="html",
        page=None,
        section="Gardening",
        token_estimate=12,
    )
    return RetrievedPassage(chunk=chunk, score=score)


def test_evidence_gate_threshold():
    assert not evidence_is_sufficient([], min_score=0.45)
    assert not evidence_is_sufficient([_passage(0.10)], min_score=0.45)
    assert not evidence_is_sufficient([_passage(0.40)], min_score=0.45)
    assert evidence_is_sufficient([_passage(0.50)], min_score=0.45)


def test_abstain_when_evidence_weak():
    result = generate_answer(
        "What is the grade replacement policy?",
        [_passage(0.05)],
    )
    assert result.status == "abstained"
    assert result.answer == ABSTAIN_MESSAGE
