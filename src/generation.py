"""Evidence gate, grounded LLM generation, and safe abstention."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.citations import format_source_block, validate_citations
from src.config import Settings, get_settings
from src.retrieval import RetrievedPassage, load_default_store, retrieve
from src.vector_store import VectorStore

logger = logging.getLogger(__name__)

ABSTAIN_MESSAGE = (
    "I could not verify an answer from the indexed official UCM documents "
    "for this question. Please check the Undergraduate or Graduate Catalog, "
    "the Student Handbook, or contact the Office of the Registrar for guidance."
)

SYSTEM_PROMPT = """You are CampusAsk, a university policy assistant for the University of Central Missouri (UCM).
Answer ONLY using the provided evidence passages. Rules:
1. Every substantive policy claim must include a citation in the form [cite:CHUNK_ID] using an ID from the evidence list.
2. If the evidence is insufficient, conflicting, or does not address the question, reply with exactly: ABSTAIN
3. Do not invent deadlines, requirements, office names, exceptions, or page numbers.
4. If undergraduate and graduate rules differ and the user level is unclear, say so and cite both when present.
5. Keep answers concise and student-friendly.
6. Never invent citation IDs that are not in the evidence list.
"""


@dataclass
class AnswerResult:
    status: str  # answered | abstained | error
    answer: str
    passages: list[RetrievedPassage] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    cited_ids: list[str] = field(default_factory=list)
    invalid_citation_ids: list[str] = field(default_factory=list)
    max_score: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "answer": self.answer,
            "sources": self.sources,
            "cited_ids": self.cited_ids,
            "invalid_citation_ids": self.invalid_citation_ids,
            "max_score": self.max_score,
            "error": self.error,
            "passage_ids": [p.chunk_id for p in self.passages],
        }


def evidence_is_sufficient(
    passages: list[RetrievedPassage],
    *,
    min_score: float,
) -> bool:
    if not passages:
        return False
    return max(p.score for p in passages) >= min_score


def _format_evidence(passages: list[RetrievedPassage]) -> str:
    blocks: list[str] = []
    for p in passages:
        loc = p.location_label()
        blocks.append(
            f"CHUNK_ID: {p.chunk_id}\n"
            f"TITLE: {p.chunk.title}\n"
            f"LEVEL: {p.chunk.level} | YEAR: {p.chunk.year}\n"
            f"LOCATION: {loc}\n"
            f"URL: {p.chunk.url}\n"
            f"TEXT: {p.chunk.text}\n"
        )
    return "\n---\n".join(blocks)


def _call_llm(prompt: str, settings: Settings) -> str:
    if not settings.llm_api_key:
        raise RuntimeError(
            "LLM_API_KEY is not set. Copy .env.example to .env and add your hosted LLM API key."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required for generation") from exc

    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    response = client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    return content.strip()


def _is_abstain_response(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return True
    if re.fullmatch(r"ABSTAIN\.?", cleaned, flags=re.IGNORECASE):
        return True
    if cleaned.upper().startswith("ABSTAIN") and len(cleaned) < 40:
        return True
    return False


def generate_answer(
    question: str,
    passages: list[RetrievedPassage],
    *,
    settings: Settings | None = None,
    academic_level: str = "all",
) -> AnswerResult:
    settings = settings or get_settings()
    max_score = max((p.score for p in passages), default=None)

    if not evidence_is_sufficient(passages, min_score=settings.evidence_min_score):
        return AnswerResult(
            status="abstained",
            answer=ABSTAIN_MESSAGE,
            passages=passages,
            sources=format_source_block(passages),
            max_score=max_score,
        )

    prompt = (
        f"Academic level filter selected by user: {academic_level}\n\n"
        f"Question: {question}\n\n"
        f"Evidence passages:\n{_format_evidence(passages)}\n\n"
        "Write the answer now. Cite with [cite:CHUNK_ID]. "
        "If evidence is insufficient, reply ABSTAIN."
    )

    try:
        raw = _call_llm(prompt, settings)
    except Exception as exc:  # noqa: BLE001
        if "LLM_API_KEY" in str(exc):
            logger.warning("LLM unavailable: %s", exc)
        else:
            logger.exception("LLM generation failed")
        return AnswerResult(
            status="error",
            answer=(
                "CampusAsk could not generate an answer because the language model "
                f"request failed: {exc}"
            ),
            passages=passages,
            sources=format_source_block(passages),
            max_score=max_score,
            error=str(exc),
        )

    if _is_abstain_response(raw):
        return AnswerResult(
            status="abstained",
            answer=ABSTAIN_MESSAGE,
            passages=passages,
            sources=format_source_block(passages),
            max_score=max_score,
        )

    check = validate_citations(raw, passages)
    # If the model cited nothing valid, treat as abstention rather than uncited claims.
    if not check.valid_ids:
        return AnswerResult(
            status="abstained",
            answer=ABSTAIN_MESSAGE,
            passages=passages,
            sources=format_source_block(passages),
            cited_ids=[],
            invalid_citation_ids=check.invalid_ids,
            max_score=max_score,
        )

    return AnswerResult(
        status="answered",
        answer=check.cleaned_answer,
        passages=passages,
        sources=format_source_block(passages, check.valid_ids),
        cited_ids=check.valid_ids,
        invalid_citation_ids=check.invalid_ids,
        max_score=max_score,
    )


def answer_question(
    question: str,
    *,
    store: VectorStore | None = None,
    settings: Settings | None = None,
    top_k: int | None = None,
    academic_level: str = "all",
    year: str | None = None,
) -> AnswerResult:
    """Unified retrieve → evidence gate → generate → citation validate path."""
    settings = settings or get_settings()
    store = store or load_default_store(settings)
    level = None if academic_level.lower() == "all" else academic_level.lower()
    passages = retrieve(
        question,
        store,
        settings=settings,
        top_k=top_k,
        level=level,
        year=year,
    )
    return generate_answer(
        question,
        passages,
        settings=settings,
        academic_level=academic_level,
    )


def answer_question_json(question: str, **kwargs: Any) -> str:
    return json.dumps(answer_question(question, **kwargs).to_dict(), indent=2)
