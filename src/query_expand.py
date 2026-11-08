"""Query rewrite / expansion for UCM policy questions.

Helps dense retrieval surface catalog language that student phrasing misses
(e.g. “thesis vs non-thesis master’s” → “thesis option / non-thesis option”).
"""

from __future__ import annotations

import re
from typing import Iterable

# Compact synonym / policy-phrase expansions keyed by trigger patterns.
_RULES: list[tuple[re.Pattern[str], list[str]]] = [
    (
        re.compile(
            r"\b(thesis|non[-\s]?thesis|non thesis)\b.*\b(master|masters|master'?s|graduate|ms|ma)\b|"
            r"\b(master|masters|master'?s|graduate|ms|ma)\b.*\b(thesis|non[-\s]?thesis)\b|"
            r"\bthesis\b.*\bnon[-\s]?thesis\b|"
            r"\bnon[-\s]?thesis\b.*\bthesis\b",
            re.IGNORECASE,
        ),
        [
            "thesis option versus non-thesis option master's degree",
            "Choose Thesis or Non-Thesis Area master's program options",
            "Policies Applying to Master's Degrees thesis non-thesis culminating experience",
        ],
    ),
    (
        re.compile(
            r"\b(gpa|grade point|good standing|academic standing)\b",
            re.IGNORECASE,
        ),
        [
            "minimum cumulative GPA grade point average academic standing requirements",
            "good academic standing GPA Graduate Undergraduate Catalog",
        ],
    ),
    (
        re.compile(r"\b(probation|academic probation|suspension)\b", re.IGNORECASE),
        [
            "academic probation cumulative GPA below requirements enrollment limits",
            "students placed on academic probation catalog policy",
        ],
    ),
    (
        re.compile(
            r"\b(credit hour|credit hours|full[-\s]?time|part[-\s]?time|course load|overload)\b",
            re.IGNORECASE,
        ),
        [
            "full-time enrollment credit hours fall spring semester",
            "maximum academic load credit hours per semester",
        ],
    ),
    (
        re.compile(r"\b(grade replacement|repeat|retake)\b", re.IGNORECASE),
        [
            "grade replacement policy retake course D or F credit hours",
        ],
    ),
    (
        re.compile(r"\b(transfer credit|transfer hours)\b", re.IGNORECASE),
        [
            "transfer credit maximum semester hours graduate undergraduate catalog",
        ],
    ),
]


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def expand_query(query: str, *, max_variants: int = 4) -> list[str]:
    """Return the original query plus up to ``max_variants - 1`` rewrites."""
    q = (query or "").strip()
    if not q:
        return []
    variants = [q]
    for pattern, expansions in _RULES:
        if pattern.search(q):
            variants.extend(expansions)
    # Light normalize: drop conversational wrappers that hurt embeddings.
    cleaned = re.sub(
        r"^(what(?:'s| is| are)|how|can you|please|tell me)\b[\s:,-]*",
        "",
        q,
        flags=re.IGNORECASE,
    ).strip(" ?.")
    if cleaned and cleaned.lower() != q.lower():
        variants.append(cleaned)
    return _unique(variants)[: max(1, max_variants)]


def _has_word(query: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", query, flags=re.IGNORECASE) is not None


def infer_level_hint(query: str) -> str | None:
    """Suggest undergraduate/graduate when the question implies a level."""
    q = (query or "").lower()
    # Prefer explicit undergraduate before substring traps ("graduate" in "undergraduate").
    ug_cues = (
        "undergraduate",
        "undergrad",
        "bachelor",
        "freshman",
        "sophomore",
        "junior",
        "senior",
    )
    grad_cues = (
        "graduate",
        "master",
        "masters",
        "master's",
        "thesis",
        "non-thesis",
        "nonthesis",
        "doctoral",
        "phd",
        "eds",
    )
    has_ug = any(_has_word(q, c) for c in ug_cues)
    has_grad = any(_has_word(q, c) for c in grad_cues)
    if has_ug and not has_grad:
        return "undergraduate"
    if has_grad and not has_ug:
        return "graduate"
    return None


def lexical_terms(query: str) -> list[str]:
    """Important multi-word / policy terms used for a soft lexical boost."""
    q = (query or "").lower()
    terms: list[str] = []
    multi = [
        "non-thesis",
        "non thesis",
        "nonthesis",
        "thesis option",
        "academic probation",
        "grade point",
        "credit hour",
        "full-time",
        "full time",
        "good standing",
        "grade replacement",
        "transfer credit",
    ]
    for term in multi:
        if term in q or any(part in q for part in term.split() if len(part) > 4):
            # Keep precise forms that appear in catalogs.
            if term in {"non thesis", "nonthesis"}:
                terms.append("non-thesis")
            elif term == "full time":
                terms.append("full-time")
            else:
                terms.append(term)
    # Always include distinctive single tokens from the question.
    for tok in re.findall(r"[a-z0-9']+", q):
        if tok in {
            "thesis",
            "gpa",
            "probation",
            "suspension",
            "overload",
            "masters",
            "master's",
        }:
            terms.append(tok)
    return _unique(terms)
