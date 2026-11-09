"""Retrieval smoke checks for catalog policy questions vs off-topic abstention."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import get_settings
from src.generation import evidence_is_sufficient
from src.retrieval import load_default_store, retrieve

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def store_and_settings():
    settings = get_settings()
    if not settings.faiss_index_path.exists() or not settings.metadata_path.exists():
        pytest.skip("FAISS index not built; run scripts/build_index.py")
    return load_default_store(settings), settings


def _max_score(passages) -> float:
    return max((p.score for p in passages), default=0.0)


def test_thesis_non_thesis_passes_evidence_gate(store_and_settings):
    store, settings = store_and_settings
    passages = retrieve(
        "What is the difference between a thesis and non-thesis master's option?",
        store,
        settings=settings,
        level="graduate",
    )
    assert passages
    assert evidence_is_sufficient(passages, min_score=settings.evidence_min_score)
    blob = " ".join(p.chunk.text.lower() for p in passages)
    assert "thesis" in blob
    # Prefer Grad Catalog general thesis / non-thesis policy language.
    assert any(
        ("non-thesis" in p.chunk.text.lower() or "non thesis" in p.chunk.text.lower())
        or "thesis option" in p.chunk.text.lower()
        or "choose thesis" in p.chunk.text.lower()
        for p in passages
    )


def test_production_retrieve_excludes_dev_fixtures(store_and_settings):
    store, settings = store_and_settings
    passages = retrieve(
        "What is the grade replacement policy for undergraduate students?",
        store,
        settings=settings,
        level="undergraduate",
        top_k=12,
    )
    assert passages
    for p in passages:
        assert "[DEV FIXTURE]" not in (p.chunk.title or "")
        assert not (p.chunk.source_id or "").startswith("fixture_")


def test_probation_gpa_passes_evidence_gate(store_and_settings):
    store, settings = store_and_settings
    passages = retrieve(
        "What GPA places an undergraduate student on academic probation?",
        store,
        settings=settings,
        level="undergraduate",
    )
    assert evidence_is_sufficient(passages, min_score=settings.evidence_min_score)
    blob = " ".join(p.chunk.text.lower() for p in passages)
    assert "probation" in blob
    assert "gpa" in blob or "grade point" in blob


def test_credit_hours_passes_evidence_gate(store_and_settings):
    store, settings = store_and_settings
    passages = retrieve(
        "How many credit hours are required for full-time graduate enrollment?",
        store,
        settings=settings,
        level="graduate",
    )
    assert evidence_is_sufficient(passages, min_score=settings.evidence_min_score)
    blob = " ".join(p.chunk.text.lower() for p in passages)
    assert "credit" in blob


def test_offtopic_fails_evidence_gate(store_and_settings):
    store, settings = store_and_settings
    passages = retrieve(
        "What is the weather in Warrensburg tomorrow?",
        store,
        settings=settings,
        level=None,
    )
    assert not evidence_is_sufficient(passages, min_score=settings.evidence_min_score)
    assert _max_score(passages) < settings.evidence_min_score


def test_computer_science_ms_overview_passes_evidence_gate(store_and_settings):
    store, settings = store_and_settings
    passages = retrieve(
        "Computer Science, MS (53-976) 30 hours Master of Science degree in Computer Science",
        store,
        settings=settings,
        level="graduate",
    )
    assert passages
    assert evidence_is_sufficient(passages, min_score=settings.evidence_min_score)
    blob = " ".join(p.chunk.text for p in passages)
    assert "Computer Science, MS" in blob
    assert "30 hours" in blob or "30" in blob


def test_masters_student_in_cs_retrieves_cs_ms(store_and_settings):
    store, settings = store_and_settings
    passages = retrieve(
        "i am masters student in computer science",
        store,
        settings=settings,
        level=None,
    )
    assert evidence_is_sufficient(passages, min_score=settings.evidence_min_score)
    blob = " ".join(p.chunk.text for p in passages)
    assert "Computer Science, MS" in blob
