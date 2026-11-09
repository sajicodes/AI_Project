"""Conversational intents must never abstain or hit RAG."""

from unittest.mock import patch

from src.conversation import (
    classify_conversational_intent,
    conversational_reply,
    detect_session_level_hint,
    rewrite_program_overview_query,
)
from src.generation import ABSTAIN_MESSAGE, answer_question


def test_classify_greetings():
    for text in ("HI", "hi", "Hello!", "hey", "Good morning", "GOOD AFTERNOON"):
        assert classify_conversational_intent(text) == "greeting"


def test_classify_thanks_goodbye_help():
    assert classify_conversational_intent("thanks") == "thanks"
    assert classify_conversational_intent("Thank you!") == "thanks"
    assert classify_conversational_intent("bye") == "goodbye"
    assert classify_conversational_intent("help") == "help"
    assert classify_conversational_intent("how are you") == "how_are_you"


def test_classify_expanded_smalltalk():
    for text in (
        "Hi how are you",
        "hi, how are you?",
        "Hey what's up",
        "what's up",
        "whats up",
        "how's it going",
        "How is it going?",
        "sup",
        "yo what's up",
    ):
        assert classify_conversational_intent(text) == "how_are_you", text


def test_classify_masters_student_context():
    for text in (
        "i am a masters student",
        "I am a master's student",
        "i'm a masters student",
        "I'm a graduate student",
        "masters student",
    ):
        assert classify_conversational_intent(text) == "student_context"
        reply = conversational_reply(text)
        assert reply is not None
        assert reply.intent == "student_context"
        assert "master" in reply.answer.lower()
        assert "credit hours" in reply.answer.lower() or "admission" in reply.answer.lower()
        assert reply.suggested_academic_level == "graduate"


def test_im_in_computer_science_is_soft_context():
    intent = classify_conversational_intent("I'm in computer science")
    assert intent == "student_context"
    reply = conversational_reply("I'm in computer science")
    assert reply is not None
    assert "Computer Science" in reply.answer
    assert reply.suggested_academic_level is None


def test_policy_questions_are_not_conversational():
    for text in (
        "What GPA places a student on academic probation?",
        "thesis vs non-thesis master's",
        "How many credit hours for full-time enrollment?",
        "What is the weather in Warrensburg tomorrow?",
        "i am masters student in computer science",
        "i am a computer science masters student",
    ):
        assert classify_conversational_intent(text) is None


def test_program_overview_rewrite_for_cs_ms():
    rewrite = rewrite_program_overview_query("i am masters student in computer science")
    assert rewrite is not None
    assert rewrite.program_label == "Computer Science"
    assert "Computer Science, MS" in rewrite.retrieval_query
    assert rewrite.suggested_academic_level == "graduate"
    assert detect_session_level_hint("i am masters student in computer science") == "graduate"


def test_named_greeting_reply():
    reply = conversational_reply("HI", first_name="Sajitha")
    assert reply is not None
    assert reply.intent == "greeting"
    assert "Sajitha" in reply.answer
    assert "catalog" in reply.answer.lower() or "policy" in reply.answer.lower()
    assert ABSTAIN_MESSAGE not in reply.answer


def test_hi_how_are_you_named_reply_never_abstains():
    reply = conversational_reply("Hi how are you", first_name="Sajitha")
    assert reply is not None
    assert reply.intent == "how_are_you"
    assert "Sajitha" in reply.answer
    assert ABSTAIN_MESSAGE not in reply.answer


def test_hi_answer_question_never_abstains_or_retrieves():
    with patch("src.generation.retrieve") as mocked_retrieve:
        with patch("src.generation.load_default_store") as mocked_store:
            result = answer_question("HI", first_name="Sajitha")
            mocked_retrieve.assert_not_called()
            mocked_store.assert_not_called()
    assert result.status == "conversational"
    assert result.intent == "greeting"
    assert "Sajitha" in result.answer
    assert result.sources == []
    assert result.answer != ABSTAIN_MESSAGE


def test_hi_how_are_you_answer_question_short_circuits():
    with patch("src.generation.retrieve") as mocked_retrieve:
        with patch("src.generation.load_default_store") as mocked_store:
            result = answer_question("Hi how are you", first_name="Alex")
            mocked_retrieve.assert_not_called()
            mocked_store.assert_not_called()
    assert result.status == "conversational"
    assert result.intent == "how_are_you"
    assert "Alex" in result.answer


def test_masters_student_context_never_retrieves():
    with patch("src.generation.retrieve") as mocked_retrieve:
        with patch("src.generation.load_default_store") as mocked_store:
            result = answer_question("i am a masters student", first_name="Alex")
            mocked_retrieve.assert_not_called()
            mocked_store.assert_not_called()
    assert result.status == "conversational"
    assert result.intent == "student_context"
    assert "master" in result.answer.lower()
    assert result.sources == []
    assert result.suggested_academic_level == "graduate"
    assert result.answer != ABSTAIN_MESSAGE


def test_masters_cs_overview_never_abstains_when_llm_abstains():
    """Known program identity must not RAG-abstain even if the model says ABSTAIN."""
    from src.chunking import Chunk
    from src.retrieval import RetrievedPassage

    fake_chunk = Chunk(
        chunk_id="grad_cs_ms_fake",
        text="Computer Science, MS (53-976) (30 hours) Department of Computer Science",
        title="UCM Graduate Catalog",
        level="graduate",
        year="2026-2027",
        source_id="fixture_grad_catalog",
        content_type="pdf",
        page=189,
        section=None,
        url="https://example.com",
        token_estimate=20,
    )
    passages = [RetrievedPassage(chunk=fake_chunk, score=0.95)]

    with patch("src.generation.retrieve", return_value=passages):
        with patch("src.generation.load_default_store"):
            with patch("src.generation._call_llm", return_value="ABSTAIN"):
                result = answer_question(
                    "I am a Masters student in computer science",
                    academic_level="undergraduate",
                )
    assert result.status == "conversational"
    assert result.status != "abstained"
    assert result.answer != ABSTAIN_MESSAGE
    assert "Computer Science" in result.answer
    assert result.suggested_academic_level == "graduate"


def test_thanks_answer_question_is_conversational():
    result = answer_question("thanks", first_name="Alex")
    assert result.status == "conversational"
    assert result.intent == "thanks"
    assert "Alex" in result.answer
