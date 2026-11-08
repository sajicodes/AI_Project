"""Conversational intents must never abstain or hit RAG."""

from unittest.mock import patch

from src.conversation import classify_conversational_intent, conversational_reply
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


def test_policy_questions_are_not_conversational():
    for text in (
        "What GPA places a student on academic probation?",
        "thesis vs non-thesis master's",
        "How many credit hours for full-time enrollment?",
        "What is the weather in Warrensburg tomorrow?",
    ):
        assert classify_conversational_intent(text) is None


def test_named_greeting_reply():
    reply = conversational_reply("HI", first_name="Sajitha")
    assert reply is not None
    assert reply.intent == "greeting"
    assert "Sajitha" in reply.answer
    assert "catalog" in reply.answer.lower() or "policy" in reply.answer.lower()
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


def test_thanks_answer_question_is_conversational():
    result = answer_question("thanks", first_name="Alex")
    assert result.status == "conversational"
    assert result.intent == "thanks"
    assert "Alex" in result.answer
