"""Evaluation harness: CampusAsk vs keyword vs ungrounded baselines + sweeps.

Does not fabricate scored results. Runs produce structure and placeholders when
the human-verified 30-question set is incomplete.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.chunking import Chunk
from src.config import Settings, get_settings
from src.generation import answer_question
from src.retrieval import retrieve
from src.vector_store import VectorStore, load_store

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkItem:
    id: str
    question: str
    category: str
    academic_level: str
    expected_abstain: bool
    gold_answer: str | None
    gold_source_ids: list[str] = field(default_factory=list)
    gold_pages_or_sections: list[str] = field(default_factory=list)
    verified: bool = False
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkItem:
        return cls(
            id=str(data["id"]),
            question=data["question"],
            category=data.get("category", "lookup"),
            academic_level=data.get("academic_level", "all"),
            expected_abstain=bool(data.get("expected_abstain", False)),
            gold_answer=data.get("gold_answer"),
            gold_source_ids=list(data.get("gold_source_ids") or []),
            gold_pages_or_sections=list(data.get("gold_pages_or_sections") or []),
            verified=bool(data.get("verified", False)),
            notes=str(data.get("notes") or ""),
        )


def load_benchmark(path: Path) -> list[BenchmarkItem]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("questions", raw if isinstance(raw, list) else [])
    return [BenchmarkItem.from_dict(q) for q in items]


def keyword_search(
    query: str,
    chunks: list[Chunk],
    *,
    top_k: int = 5,
) -> list[tuple[Chunk, float]]:
    """Simple TF-style keyword baseline over chunk text."""
    terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9']+", query) if len(t) > 2]
    if not terms:
        return []
    scored: list[tuple[Chunk, float]] = []
    for chunk in chunks:
        text = chunk.text.lower()
        hits = sum(text.count(term) for term in terms)
        if hits:
            scored.append((chunk, float(hits)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def ungrounded_stub(question: str) -> dict[str, Any]:
    """Baseline marker: answers without retrieval (not executed without an API key)."""
    return {
        "system": "ungrounded_chatbot",
        "question": question,
        "note": (
            "Ungrounded baseline requires a separate LLM call without retrieved "
            "context. Not executed in this harness run unless explicitly enabled; "
            "no fabricated answers are stored."
        ),
        "executed": False,
    }


def retrieval_hit(
    item: BenchmarkItem,
    retrieved_chunk_ids: list[str],
    store_chunks: list[Chunk],
) -> bool | None:
    """Heuristic hit: any gold source_id appears among retrieved chunks' source_ids."""
    if not item.gold_source_ids:
        return None
    by_id = {c.chunk_id: c for c in store_chunks}
    retrieved_sources = {
        by_id[cid].source_id for cid in retrieved_chunk_ids if cid in by_id
    }
    return any(sid in retrieved_sources for sid in item.gold_source_ids)


def run_single(
    item: BenchmarkItem,
    store: VectorStore,
    settings: Settings,
    *,
    top_k: int,
) -> dict[str, Any]:
    campus = answer_question(
        item.question,
        store=store,
        settings=settings,
        top_k=top_k,
        academic_level=item.academic_level,
    )
    kw = keyword_search(item.question, store.chunks, top_k=top_k)
    passages = retrieve(
        item.question,
        store,
        settings=settings,
        top_k=top_k,
        level=None if item.academic_level == "all" else item.academic_level,
    )
    hit = retrieval_hit(item, [p.chunk_id for p in passages], store.chunks)
    abstain_ok: bool | None = None
    if item.expected_abstain:
        abstain_ok = campus.status == "abstained"

    return {
        "id": item.id,
        "question": item.question,
        "category": item.category,
        "verified": item.verified,
        "campusask": {
            "status": campus.status,
            "answer": campus.answer,
            "cited_ids": campus.cited_ids,
            "max_score": campus.max_score,
        },
        "keyword_baseline": [
            {"chunk_id": c.chunk_id, "score": s, "title": c.title} for c, s in kw
        ],
        "ungrounded_baseline": ungrounded_stub(item.question),
        "retrieval_hit": hit,
        "abstention_correct": abstain_ok,
        "human_accuracy": None,
        "human_hallucination": None,
        "notes": (
            "Accuracy and hallucination require dual human review against verified "
            "gold answers. Fields left null until scored."
        ),
    }


def run_evaluation(
    benchmark_path: Path,
    *,
    settings: Settings | None = None,
    chunk_sizes: list[int] | None = None,
    k_values: list[int] | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Run evaluation structure. Sweep metadata is recorded; index rebuild for
    alternate chunk sizes is left to scripts/build_index.py with env overrides.
    """
    settings = settings or get_settings()
    out_dir = out_dir or settings.results_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    items = load_benchmark(benchmark_path)
    verified_count = sum(1 for i in items if i.verified)
    store = load_store(settings.faiss_index_path, settings.metadata_path)

    k_values = k_values or [3, 5, 10]
    chunk_sizes = chunk_sizes or [300, 500, 800]

    primary_k = settings.top_k
    rows = [run_single(item, store, settings, top_k=primary_k) for item in items]

    summary = {
        "targets": {
            "answer_accuracy": ">= 0.80 (human dual review; not claimed here)",
            "retrieval_hit_rate": ">= 0.90",
            "hallucination_rate": "<= 0.10 (human review; not claimed here)",
            "appropriate_abstention": ">= 0.80",
        },
        "benchmark": {
            "path": str(benchmark_path),
            "n_questions": len(items),
            "n_verified": verified_count,
            "ready_for_scored_reporting": verified_count >= 30 and all(i.verified for i in items[:30]),
        },
        "config": {
            "embedding_model": settings.embedding_model,
            "chunk_size_index": settings.chunk_size,
            "top_k": primary_k,
            "evidence_min_score": settings.evidence_min_score,
            "llm_model": settings.llm_model,
            "planned_chunk_sweeps": chunk_sizes,
            "planned_k_sweeps": k_values,
            "sweep_note": (
                "Rebuild the FAISS index with CHUNK_SIZE set for each chunk sweep "
                "before comparing retrieval quality across chunk sizes."
            ),
        },
        "aggregate": {
            "retrieval_hit_rate": _rate([r["retrieval_hit"] for r in rows]),
            "abstention_correct_rate": _rate([r["abstention_correct"] for r in rows]),
            "answer_accuracy": None,
            "hallucination_rate": None,
        },
        "rows": rows,
    }

    out_path = out_dir / "evaluation_run.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Wrote evaluation structure to %s", out_path)
    return summary


def _rate(values: list[bool | None]) -> float | None:
    usable = [v for v in values if v is not None]
    if not usable:
        return None
    return sum(1 for v in usable if v) / len(usable)


def benchmark_template() -> dict[str, Any]:
    """Schema/template for the 30-Q human-verified set — no fabricated gold answers."""
    categories = [
        ("lookup", False),
        ("conditional", False),
        ("multi_source", False),
        ("ug_vs_grad", False),
        ("unanswerable", True),
    ]
    questions: list[dict[str, Any]] = []
    for i in range(1, 31):
        cat, abstain = categories[(i - 1) % len(categories)]
        questions.append(
            {
                "id": f"Q{i:02d}",
                "question": f"[TEAM TO WRITE] Benchmark question {i} ({cat})",
                "category": cat,
                "academic_level": "undergraduate"
                if cat == "ug_vs_grad" and i % 2
                else ("graduate" if cat == "ug_vs_grad" else "all"),
                "expected_abstain": abstain,
                "gold_answer": None,
                "gold_source_ids": [],
                "gold_pages_or_sections": [],
                "verified": False,
                "notes": "Replace placeholder with a human-verified question and gold answer.",
            }
        )
    return {
        "description": (
            "30-question CampusAsk benchmark template. Gold answers and source "
            "locations must be dual-reviewed by the team before reporting metrics."
        ),
        "targets": {
            "answer_accuracy": 0.80,
            "retrieval_hit_rate": 0.90,
            "hallucination_rate": 0.10,
            "appropriate_abstention": 0.80,
        },
        "questions": questions,
    }
