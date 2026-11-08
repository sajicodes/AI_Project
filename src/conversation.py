"""Lightweight conversational intents for CampusAsk (no RAG).

Greetings, thanks, goodbye, and light help/how-are-you must never hit
retrieval or the evidence gate. Policy/catalog questions stay RAG-routed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Whole-utterance patterns — keep tight so real policy Qs still go to RAG.
_GREETING = re.compile(
    r"^\s*("
    r"hi+|hello+|hey+|howdy|"
    r"good\s*(morning|afternoon|evening|day)|"
    r"greetings|"
    r"yo+"
    r")[\s!.?]*$",
    re.IGNORECASE,
)
_THANKS = re.compile(
    r"^\s*("
    r"thanks(?:\s+you)?|thank\s*you|thx|ty|"
    r"appreciate\s+it|much\s+appreciated"
    r")[\s!.?]*$",
    re.IGNORECASE,
)
_GOODBYE = re.compile(
    r"^\s*("
    r"bye+|goodbye|good\s*bye|see\s+ya|see\s+you|"
    r"later|take\s+care|have\s+a\s+(good|nice)\s+(day|one)"
    r")[\s!.?]*$",
    re.IGNORECASE,
)
_HELP = re.compile(
    r"^\s*("
    r"help(?:\s+me)?|"
    r"what\s+can\s+you\s+(do|help\s+with)|"
    r"how\s+(do\s+i|to)\s+use\s+(this|campusask)|"
    r"what\s+is\s+campusask"
    r")[\s!.?]*$",
    re.IGNORECASE,
)
_HOWAREYOU = re.compile(
    r"^\s*("
    r"how\s+are\s+you(?:\s+doing)?|"
    r"how(?:'s|\s+is)\s+it\s+going|"
    r"what'?s\s+up|"
    r"how\s+do\s+you\s+do"
    r")[\s!.?]*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ConversationalReply:
    intent: str  # greeting | thanks | goodbye | help | how_are_you
    answer: str


def classify_conversational_intent(text: str) -> str | None:
    """Return an intent label for chitchat, else None (route to RAG)."""
    raw = (text or "").strip()
    if not raw:
        return None
    # Very short emoji/punctuation-only chatter
    if re.fullmatch(r"[\W_]+", raw) and len(raw) <= 8:
        return "greeting"
    if _GREETING.match(raw):
        return "greeting"
    if _THANKS.match(raw):
        return "thanks"
    if _GOODBYE.match(raw):
        return "goodbye"
    if _HELP.match(raw):
        return "help"
    if _HOWAREYOU.match(raw):
        return "how_are_you"
    return None


def conversational_reply(
    text: str,
    *,
    first_name: str | None = None,
) -> ConversationalReply | None:
    """Build a short polite desk reply, or None if this is a policy question."""
    intent = classify_conversational_intent(text)
    if intent is None:
        return None

    name = (first_name or "").strip()
    named = bool(name) and name.lower() not in {"there", ""}

    if intent == "greeting":
        if named:
            answer = (
                f"Hi {name}! How can I help with a UCM catalog or policy question today?"
            )
        else:
            answer = (
                "Hello! I'm CampusAsk at the Academic Catalog Desk. "
                "Ask me a UCM catalog or policy question whenever you're ready."
            )
    elif intent == "thanks":
        if named:
            answer = (
                f"You're welcome, {name}. Happy to help with another catalog question anytime."
            )
        else:
            answer = "You're welcome. Happy to help with another catalog question anytime."
    elif intent == "goodbye":
        if named:
            answer = f"Goodbye, {name}. Take care — the Academic Catalog Desk is here when you need it."
        else:
            answer = "Goodbye! Take care — the Academic Catalog Desk is here when you need it."
    elif intent == "how_are_you":
        if named:
            answer = (
                f"Doing well, thanks {name}! What UCM catalog or policy question can I help with?"
            )
        else:
            answer = (
                "Doing well, thank you! What UCM catalog or policy question can I help with?"
            )
    else:  # help
        answer = (
            "I look up official UCM Undergraduate and Graduate Catalog policy and "
            "cite the source — or clearly say when the catalogs don't cover it. "
            "Try asking about GPA, probation, credit hours, or thesis vs non-thesis options."
        )

    return ConversationalReply(intent=intent, answer=answer)
