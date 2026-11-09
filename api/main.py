"""FastAPI service for CampusAsk RAG + conversation + identity validation.

Deploy this process on Railway / Render / Fly. The Next.js app (Vercel)
talks to it via NEXT_PUBLIC_API_URL. Never log UCM IDs.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import Settings, get_settings  # noqa: E402
from src.generation import answer_question  # noqa: E402
from src.identity import (  # noqa: E402
    build_identity,
    validate_full_name,
    validate_ucm_id,
    welcome_greeting,
)
from src.branding import SAMPLE_QUESTIONS  # noqa: E402
from src.vector_store import VectorStore, load_store  # noqa: E402

logger = logging.getLogger("campusask.api")
logging.basicConfig(level=logging.INFO)

_store: VectorStore | None = None
_settings: Settings | None = None


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [part.strip() for part in raw.split(",") if part.strip()]


def get_cached_store() -> tuple[VectorStore, Settings]:
    global _store, _settings
    if _store is None or _settings is None:
        settings = get_settings()
        _store = load_store(settings.faiss_index_path, settings.metadata_path)
        _settings = settings
        logger.info(
            "Loaded FAISS index from %s (%s chunks)",
            settings.faiss_index_path,
            len(_store.chunks) if hasattr(_store, "chunks") else "?",
        )
    return _store, _settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Warm the index at boot so the first Ask is not a cold FAISS load.
    try:
        get_cached_store()
    except FileNotFoundError as exc:
        logger.warning("Index not available at startup: %s", exc)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to warm CampusAsk index at startup")
    yield


app = FastAPI(
    title="CampusAsk API",
    description="Grounded UCM academic catalog Q&A (FAISS + Groq).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    academic_level: Literal["all", "undergraduate", "graduate"] = "all"
    first_name: str | None = Field(
        default=None,
        max_length=40,
        description="First name only for greetings. Never send UCM ID.",
    )


class AskResponse(BaseModel):
    status: str
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    cited_ids: list[str] = Field(default_factory=list)
    invalid_citation_ids: list[str] = Field(default_factory=list)
    max_score: float | None = None
    error: str | None = None
    intent: str | None = None
    suggested_academic_level: Literal["undergraduate", "graduate"] | None = None


class IdentityRequest(BaseModel):
    full_name: str = Field(..., max_length=80)
    ucm_id: str = Field(..., max_length=20)


class IdentityResponse(BaseModel):
    ok: bool
    full_name: str | None = None
    first_name: str | None = None
    masked_id: str | None = None
    greeting: str | None = None
    errors: dict[str, str] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, Any]:
    index_ok = False
    chunk_count: int | None = None
    try:
        store, settings = get_cached_store()
        index_ok = True
        chunk_count = len(getattr(store, "chunks", []) or [])
        has_key = bool(settings.llm_api_key)
    except Exception:  # noqa: BLE001
        has_key = bool(os.getenv("LLM_API_KEY", ""))
    return {
        "status": "ok",
        "service": "campusask-api",
        "index_loaded": index_ok,
        "chunk_count": chunk_count,
        "llm_configured": has_key,
    }


@app.get("/v1/samples")
def samples() -> dict[str, Any]:
    return {"samples": SAMPLE_QUESTIONS}


@app.post("/v1/identity/validate", response_model=IdentityResponse)
def identity_validate(body: IdentityRequest) -> IdentityResponse:
    """Validate Name + UCM ID. Returns masked ID only — never echo full ID in logs."""
    errors: dict[str, str] = {}
    name_err = validate_full_name(body.full_name)
    id_err = validate_ucm_id(body.ucm_id)
    if name_err:
        errors["full_name"] = name_err
    if id_err:
        errors["ucm_id"] = id_err
    if errors:
        return IdentityResponse(ok=False, errors=errors)

    identity = build_identity(body.full_name, body.ucm_id)
    return IdentityResponse(
        ok=True,
        full_name=identity.full_name,
        first_name=identity.first_name,
        masked_id=identity.masked_id,
        greeting=welcome_greeting(identity.first_name),
    )


@app.post("/v1/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    first_name = (body.first_name or "").strip() or None
    # Conversational path never needs the index.
    from src.conversation import classify_conversational_intent

    is_chitchat = classify_conversational_intent(question) is not None
    try:
        if is_chitchat:
            result = answer_question(
                question,
                academic_level=body.academic_level,
                first_name=first_name,
            )
        else:
            store, settings = get_cached_store()
            result = answer_question(
                question,
                store=store,
                settings=settings,
                academic_level=body.academic_level,
                first_name=first_name,
            )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ask failed")
        raise HTTPException(status_code=500, detail="CampusAsk ask failed.") from exc

    suggested = getattr(result, "suggested_academic_level", None)
    if suggested not in {"undergraduate", "graduate"}:
        suggested = None

    return AskResponse(
        status=result.status,
        answer=result.answer,
        sources=[] if result.status == "conversational" else result.sources,
        cited_ids=result.cited_ids,
        invalid_citation_ids=result.invalid_citation_ids,
        max_score=result.max_score,
        error=result.error,
        intent=result.intent,
        suggested_academic_level=suggested,
    )


def create_app() -> FastAPI:
    return app
