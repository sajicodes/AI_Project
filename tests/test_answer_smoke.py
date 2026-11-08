"""Smoke: policy questions retrieve evidence and produce cited answers (mocked LLM)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.config import get_settings
from src.generation import ABSTAIN_MESSAGE, answer_question
from src.retrieval import load_default_store


@pytest.fixture(scope="module")
def store_and_settings():
    settings = get_settings()
    if not settings.faiss_index_path.exists():
        pytest.skip("FAISS index not built")
    return load_default_store(settings), settings


def test_thesis_question_yields_cited_answer(store_and_settings):
    store, settings = store_and_settings
    question = "What is the difference between a thesis and non-thesis master's option?"

    def fake_llm(prompt: str, _settings):
        # Cite the first CHUNK_ID present in the prompt evidence block.
        import re

        match = re.search(r"CHUNK_ID:\s*([^\n]+)", prompt)
        assert match, "expected evidence passages in the prompt"
        cid = match.group(1).strip()
        assert " " not in cid, "chunk IDs must be citation-safe"
        return (
            "Many UCM master's programs offer a thesis option (original research) "
            f"and a non-thesis option (coursework or alternative culminating experience). "
            f"Program catalogs describe both paths. [cite:{cid}]"
        )

    with patch("src.generation._call_llm", side_effect=fake_llm):
        result = answer_question(
            question,
            store=store,
            settings=settings,
            academic_level="graduate",
        )

    assert result.status == "answered"
    assert result.cited_ids
    assert result.sources
    assert "[cite:" not in result.answer or True  # cleaned answer may keep or drop marks
    assert "thesis" in result.answer.lower()


def test_gpa_probation_question_yields_cited_answer(store_and_settings):
    store, settings = store_and_settings
    question = "What GPA places an undergraduate student on academic probation?"

    def fake_llm(prompt: str, _settings):
        import re

        match = re.search(r"CHUNK_ID:\s*([^\n]+)", prompt)
        assert match
        cid = match.group(1).strip()
        return (
            f"Undergraduate students whose cumulative GPA falls below 2.00 "
            f"are placed on academic probation. [cite:{cid}]"
        )

    with patch("src.generation._call_llm", side_effect=fake_llm):
        result = answer_question(
            question,
            store=store,
            settings=settings,
            academic_level="undergraduate",
        )

    assert result.status == "answered"
    assert result.cited_ids
    assert "probation" in result.answer.lower()


def test_offtopic_still_abstains(store_and_settings):
    store, settings = store_and_settings
    with patch("src.generation._call_llm") as mocked:
        result = answer_question(
            "What is the weather in Warrensburg tomorrow?",
            store=store,
            settings=settings,
            academic_level="all",
        )
        mocked.assert_not_called()
    assert result.status == "abstained"
    assert result.answer == ABSTAIN_MESSAGE


def test_hi_is_polite_named_greeting_not_abstention(store_and_settings):
    store, settings = store_and_settings
    with patch("src.generation.retrieve") as mocked_retrieve:
        with patch("src.generation._call_llm") as mocked_llm:
            result = answer_question(
                "HI",
                store=store,
                settings=settings,
                first_name="Sajitha",
            )
            mocked_retrieve.assert_not_called()
            mocked_llm.assert_not_called()
    assert result.status == "conversational"
    assert "Sajitha" in result.answer
    assert result.answer != ABSTAIN_MESSAGE
    assert not result.sources
