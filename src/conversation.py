"""Lightweight conversational intents for CampusAsk (no RAG).

Greetings, thanks, goodbye, light help/how-are-you, and vague student-context
statements must never hit retrieval or the evidence gate. Policy/catalog
questions stay RAG-routed. Program identity like “masters student in computer
science” is rewritten for retrieval in generation (not abstained).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Optional greeting lead-in before how-are-you / what's-up small talk.
_GREETING_LEAD = r"(?:(?:hi+|hello+|hey+|howdy|yo+)\s*[,!]?\s*)?"

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
    rf"^\s*{_GREETING_LEAD}("
    r"how\s+are\s+you(?:\s+doing)?|"
    r"how(?:'s|\s+is)\s+it\s+going|"
    r"what'?s\s+up|"
    r"whats\s+up|"
    r"sup|"
    r"how\s+do\s+you\s+do"
    r")[\s!.?]*$",
    re.IGNORECASE,
)

_I_AM = r"(?:i\s*(?:'m|am)|im)"
_GRAD_STUDENT = (
    r"(?:a\s+|an\s+)?"
    r"(?:masters?|master'?s|ms|m\.s\.?|graduate|grad)\s+"
    r"(?:degree\s+)?student"
)
_UG_STUDENT = (
    r"(?:a\s+|an\s+)?"
    r"(?:undergraduate|undergrad|bachelor'?s?)\s+"
    r"(?:degree\s+)?student"
)

# Vague level-only context — no program, no question verb.
_STUDENT_CONTEXT_GRAD = re.compile(
    rf"^\s*{_I_AM}\s+{_GRAD_STUDENT}\s*[!.]*$",
    re.IGNORECASE,
)
_STUDENT_CONTEXT_UG = re.compile(
    rf"^\s*{_I_AM}\s+{_UG_STUDENT}\s*[!.]*$",
    re.IGNORECASE,
)
# Bare “masters student” / “graduate student” without “I am”.
_STUDENT_CONTEXT_BARE = re.compile(
    r"^\s*(?:just\s+)?(?:"
    r"(?:a\s+|an\s+)?(?:masters?|master'?s|ms|graduate|grad)\s+(?:degree\s+)?student|"
    r"(?:a\s+|an\s+)?(?:undergraduate|undergrad)\s+(?:degree\s+)?student"
    r")\s*[!.]*$",
    re.IGNORECASE,
)

# Identity + program (e.g. “i am masters student in computer science”).
_PROGRAM_CONTEXT = re.compile(
    rf"^\s*{_I_AM}\s+(?:"
    rf"(?P<grad>{_GRAD_STUDENT})\s+(?:in|studying|of)\s+(?P<program>.+?)|"
    rf"(?P<ug>{_UG_STUDENT})\s+(?:in|studying|of)\s+(?P<program_ug>.+?)|"
    rf"(?:a\s+|an\s+)?(?P<pre_program>[\w\s.&/-]+?)\s+"
    rf"(?:masters?|master'?s|ms|m\.s\.?|graduate)\s+(?:degree\s+)?student|"
    rf"(?:in|studying)\s+(?P<program_only>.+?)"
    rf")\s*[!.]*$",
    re.IGNORECASE,
)

_QUESTIONISH = re.compile(
    r"\b("
    r"what|when|where|which|who|why|how|"
    r"can|could|would|should|does|do|did|is|are|will|"
    r"tell\s+me|explain|list|difference|require|needed|need\b|"
    r"credit\s+hours?|gpa|probation|thesis|options?"
    r")\b",
    re.IGNORECASE,
)

# Known program aliases → catalog retrieval phrasing.
_PROGRAM_ALIASES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\b(?:computer\s*science|comp\s*sci|\bcs\b)\b", re.IGNORECASE),
        "Computer Science",
        (
            "Computer Science, MS (53-976) 30 hours "
            "Department of Computer Science and Cybersecurity "
            "Master of Science degree in Computer Science requirements "
            "admission thesis project options"
        ),
    ),
]


@dataclass(frozen=True)
class ConversationalReply:
    intent: str  # greeting | thanks | goodbye | help | how_are_you | student_context
    answer: str
    suggested_academic_level: str | None = None


@dataclass(frozen=True)
class ProgramOverviewRewrite:
    """Identity + program with no concrete question → retrieve a catalog overview."""

    program_label: str
    retrieval_query: str
    llm_question: str
    suggested_academic_level: str | None
    soft_prompt: str


def detect_session_level_hint(text: str) -> str | None:
    """Return undergraduate/graduate when the utterance declares a student level."""
    raw = (text or "").strip().lower()
    if not raw:
        return None
    if re.search(
        r"\b(?:masters?|master'?s|ms|m\.s\.?|graduate|grad)\b",
        raw,
        flags=re.IGNORECASE,
    ) and not re.search(r"\bundergraduate|undergrad|bachelor", raw, flags=re.IGNORECASE):
        return "graduate"
    if re.search(r"\b(?:undergraduate|undergrad|bachelor'?s?)\b", raw, flags=re.IGNORECASE):
        return "undergraduate"
    return None


def _match_program(fragment: str) -> tuple[str, str] | None:
    text = (fragment or "").strip(" .!?")
    if not text:
        return None
    for pattern, label, retrieval in _PROGRAM_ALIASES:
        if pattern.search(text):
            return label, retrieval
    return None


def rewrite_program_overview_query(text: str) -> ProgramOverviewRewrite | None:
    """If the user only states program context, rewrite into a CS/program overview query.

    Returns None when the utterance is a real policy question or not program context.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    # Real questions keep the normal RAG path (expansion still helps).
    if _QUESTIONISH.search(raw) and not _PROGRAM_CONTEXT.match(raw):
        return None
    # If it clearly asks something beyond identity, skip rewrite.
    if re.search(
        r"\b(what|when|where|which|who|why|how|difference|require|credit\s+hours?|gpa|probation)\b",
        raw,
        flags=re.IGNORECASE,
    ) and not re.match(
        rf"^\s*{_I_AM}\b",
        raw,
        flags=re.IGNORECASE,
    ):
        return None

    match = _PROGRAM_CONTEXT.match(raw)
    if not match:
        return None

    groups = match.groupdict()
    program_fragment = (
        groups.get("program")
        or groups.get("program_ug")
        or groups.get("pre_program")
        or groups.get("program_only")
        or ""
    )
    hit = _match_program(program_fragment)
    if hit is None:
        # Unknown program: soft conversational handling via student_context-like reply
        # is done by callers when rewrite is None and classify returns student_context.
        return None

    label, retrieval_query = hit
    level = detect_session_level_hint(raw)
    # “I'm in computer science” without masters → still offer CS MS overview soft path
    # only when graduate cues exist; otherwise soft-prompt for level.
    if level is None and groups.get("program_only"):
        return None

    soft = (
        f"Got it — {label} master's student. "
        "Ask about credit hours, GPA, probation, thesis, or your program."
    )
    llm_question = (
        f"What are the Graduate Catalog requirements for the {label} MS program "
        f"(total hours, options such as thesis/project, and key program notes)?"
    )
    return ProgramOverviewRewrite(
        program_label=label,
        retrieval_query=retrieval_query,
        llm_question=llm_question,
        suggested_academic_level=level or "graduate",
        soft_prompt=soft,
    )


def classify_conversational_intent(text: str) -> str | None:
    """Return an intent label for chitchat, else None (route to RAG)."""
    raw = (text or "").strip()
    if not raw:
        return None
    # Very short emoji/punctuation-only chatter
    if re.fullmatch(r"[\W_]+", raw) and len(raw) <= 8:
        return "greeting"
    # Prefer how-are-you before bare greeting so "Hi how are you" is never RAG.
    if _HOWAREYOU.match(raw):
        return "how_are_you"
    if _GREETING.match(raw):
        return "greeting"
    if _THANKS.match(raw):
        return "thanks"
    if _GOODBYE.match(raw):
        return "goodbye"
    if _HELP.match(raw):
        return "help"
    # Program overview statements are RAG-routed (rewritten), not chitchat.
    if rewrite_program_overview_query(raw) is not None:
        return None
    if (
        _STUDENT_CONTEXT_GRAD.match(raw)
        or _STUDENT_CONTEXT_UG.match(raw)
        or _STUDENT_CONTEXT_BARE.match(raw)
    ):
        return "student_context"
    # “I'm in computer science” without masters → soft context, no RAG abstention.
    prog_only = _PROGRAM_CONTEXT.match(raw)
    if prog_only and prog_only.groupdict().get("program_only"):
        if _match_program(prog_only.groupdict().get("program_only") or ""):
            return "student_context"
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
    level_hint = detect_session_level_hint(text)

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
    elif intent == "student_context":
        raw_l = (text or "").lower()
        prog = _PROGRAM_CONTEXT.match((text or "").strip())
        program_label = None
        if prog:
            fragment = prog.groupdict().get("program_only") or ""
            hit = _match_program(fragment)
            if hit:
                program_label = hit[0]
        if program_label:
            answer = (
                f"Got it — {program_label}. "
                "Are you undergraduate or graduate? Ask about credit hours, GPA, "
                "probation, thesis, or your program."
            )
            level_hint = None
        elif level_hint == "graduate" or re.search(
            r"master|grad", raw_l, flags=re.IGNORECASE
        ):
            answer = (
                "Got it — master's student. Ask about credit hours, GPA, probation, "
                "thesis, or your program."
            )
            level_hint = "graduate"
        elif level_hint == "undergraduate":
            answer = (
                "Got it — undergraduate student. Ask about credit hours, GPA, "
                "probation, or your major requirements."
            )
        else:
            answer = (
                "Got it. Ask about credit hours, GPA, probation, thesis, or your program."
            )
    else:  # help
        answer = (
            "I look up official UCM Undergraduate and Graduate Catalog policy and "
            "cite the source — or clearly say when the catalogs don't cover it. "
            "Try asking about GPA, probation, credit hours, or thesis vs non-thesis options."
        )

    return ConversationalReply(
        intent=intent,
        answer=answer,
        suggested_academic_level=level_hint,
    )
