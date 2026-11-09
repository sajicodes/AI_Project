"""Shared Ask-experience helpers for CampusAsk."""

from __future__ import annotations

import html
import logging

import streamlit as st

from src.config import get_settings
from src.generation import answer_question
from src.ui.identity import (
    clear_identity,
    consume_greeting,
    get_identity,
    render_identity_gate,
)
from src.ui.theme import (
    SAMPLE_QUESTIONS,
    render_ask_empty_state,
    render_ask_topbar,
    render_sidebar_brand,
)
from src.vector_store import load_store

logger = logging.getLogger(__name__)


@st.cache_resource(show_spinner=False)
def get_store():
    """Load FAISS index once per process; caller shows spinner when needed."""
    settings = get_settings()
    return load_store(settings.faiss_index_path, settings.metadata_path), settings


def render_sources(sources: list[dict]) -> None:
    if not sources:
        st.markdown(
            '<p class="empty-hint">No retrieved passages to display.</p>',
            unsafe_allow_html=True,
        )
        return
    for src in sources:
        title = html.escape(str(src.get("title") or "Untitled source"))
        loc = html.escape(str(src.get("location") or ""))
        url = str(src.get("url") or "")
        excerpt = html.escape(str(src.get("excerpt") or ""))
        level = html.escape(str(src.get("level") or ""))
        year = html.escape(str(src.get("year") or ""))
        score = src.get("score")
        score_bit = (
            f" · Relevance {float(score):.2f}" if isinstance(score, (int, float)) else ""
        )
        safe_url = html.escape(url, quote=True)
        link = (
            f'<a href="{safe_url}" target="_blank" rel="noopener">Open source</a>'
            if url
            else ""
        )
        st.markdown(
            f"""
            <div class="source-card">
              <h4>{title}</h4>
              <div class="source-meta">{loc} · Level: {level} · Year: {year}{score_bit} · {link}</div>
              <div class="source-excerpt">{excerpt}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_ask_sidebar() -> str:
    identity = get_identity()
    with st.sidebar:
        render_sidebar_brand()
        if identity:
            st.markdown(
                f"""
                <div class="student-chip">
                  <p class="student-chip-label">Signed in</p>
                  <p class="student-chip-name">{html.escape(identity.full_name)}</p>
                  <p class="student-chip-id">UCM ID {html.escape(identity.masked_id)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("---")
        level = st.selectbox(
            "Academic level",
            options=["All", "Undergraduate", "Graduate"],
            index=0,
            help="Filters retrieval toward matching catalog level when metadata allows.",
        )
        if st.button("New conversation", use_container_width=True):
            st.session_state.messages = []
            # Keep identity; allow greeting-less fresh chat.
            st.rerun()
        if identity and st.button("Switch student", use_container_width=True):
            clear_identity()
            st.rerun()
        if st.button("Back to home", use_container_width=True, type="secondary"):
            st.switch_page("app.py")
    return level


def _render_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            status = message.get("status")
            if message["role"] == "assistant" and status:
                if status == "answered":
                    st.markdown(
                        '<p class="status-ok">From the catalogs</p>',
                        unsafe_allow_html=True,
                    )
                elif status == "abstained":
                    st.markdown(
                        '<p class="status-abstain">I couldn\'t find this in the catalogs</p>',
                        unsafe_allow_html=True,
                    )
                elif status == "greeting":
                    st.markdown(
                        '<p class="status-ok">Welcome</p>',
                        unsafe_allow_html=True,
                    )
                elif status == "conversational":
                    pass  # Natural desk reply — no status chrome
                elif status == "error":
                    st.markdown(
                        '<p class="status-err">Generation error</p>',
                        unsafe_allow_html=True,
                    )
            st.markdown(message["content"])
            if message.get("sources") and message.get("status") != "conversational":
                with st.expander("Sources & evidence", expanded=False):
                    render_sources(message["sources"])


def _seed_greeting_if_needed() -> None:
    greeting = consume_greeting()
    if not greeting:
        return
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": greeting,
            "sources": [],
            "status": "greeting",
        }
    )


def _render_sample_chips() -> str | None:
    """Clickable sample questions; returns selected prompt if any."""
    st.markdown(
        '<p class="chip-label">Try a catalog question</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(SAMPLE_QUESTIONS))
    chosen: str | None = None
    for col, sample in zip(cols, SAMPLE_QUESTIONS):
        with col:
            if st.button(sample["label"], key=f"chip_{sample['id']}", use_container_width=True):
                chosen = sample["question"]
    return chosen


def _answer_prompt(prompt: str, academic_level: str) -> None:
    from src.conversation import classify_conversational_intent

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    identity = get_identity()
    first_name = identity.first_name if identity else None
    is_chitchat = classify_conversational_intent(prompt) is not None

    with st.chat_message("assistant"):
        if is_chitchat:
            # Never load the index or show Sources for greetings/thanks/etc.
            result = answer_question(
                prompt,
                academic_level=academic_level,
                first_name=first_name,
            )
            st.markdown(result.answer)
        else:
            with st.spinner("Searching catalogs and drafting a grounded answer…"):
                try:
                    store, settings = get_store()
                except FileNotFoundError as exc:
                    st.error(str(exc))
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": str(exc),
                            "sources": [],
                            "status": "error",
                        }
                    )
                    return
                except Exception:  # noqa: BLE001
                    logger.exception("Index load failed")
                    st.error(
                        "Could not load the CampusAsk index. Rebuild with scripts/build_index.py."
                    )
                    st.caption("Index unavailable.")
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": "Index unavailable.",
                            "sources": [],
                            "status": "error",
                        }
                    )
                    return

                # Never pass UCM ID into generation / logs — first name only.
                result = answer_question(
                    prompt,
                    store=store,
                    settings=settings,
                    academic_level=academic_level,
                    first_name=first_name,
                )

            if result.status == "answered":
                st.markdown(
                    '<p class="status-ok">From the catalogs</p>',
                    unsafe_allow_html=True,
                )
            elif result.status == "abstained":
                st.markdown(
                    '<p class="status-abstain">I couldn\'t find this in the catalogs</p>',
                    unsafe_allow_html=True,
                )
            elif result.status == "error":
                st.markdown(
                    '<p class="status-err">Generation error</p>',
                    unsafe_allow_html=True,
                )

            st.markdown(result.answer)
            if result.status != "conversational":
                with st.expander(
                    "Sources & evidence", expanded=result.status == "answered"
                ):
                    render_sources(result.sources)
                    if result.cited_ids:
                        st.caption("Cited chunk IDs: " + ", ".join(result.cited_ids))
                    if result.invalid_citation_ids:
                        st.caption(
                            "Removed invalid citation IDs: "
                            + ", ".join(result.invalid_citation_ids)
                        )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.answer,
            "sources": [] if result.status == "conversational" else result.sources,
            "status": result.status,
        }
    )


def render_ask_experience() -> None:
    """Identity-gated grounded chat with sample chips and polished states."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    level = render_ask_sidebar()
    render_ask_topbar()

    if not render_identity_gate():
        st.markdown(
            '<p class="empty-hint">Ask is locked until student check-in is complete.</p>',
            unsafe_allow_html=True,
        )
        return

    _seed_greeting_if_needed()

    only_greeting = (
        len(st.session_state.messages) == 1
        and st.session_state.messages[0].get("status") == "greeting"
    )
    if not st.session_state.messages or only_greeting:
        if only_greeting:
            _render_history()
        else:
            render_ask_empty_state()
        chip_prompt = _render_sample_chips()
    else:
        _render_history()
        chip_prompt = None

    level_map = {
        "All": "all",
        "Undergraduate": "undergraduate",
        "Graduate": "graduate",
    }
    academic_level = level_map[level]

    prompt = st.chat_input("Ask a UCM policy question…")
    if chip_prompt and not prompt:
        prompt = chip_prompt
    if not prompt:
        return

    _answer_prompt(prompt, academic_level)
