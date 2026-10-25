"""Shared Ask-experience helpers for CampusAsk."""

from __future__ import annotations

import html

import streamlit as st

from src.config import get_settings
from src.generation import answer_question
from src.ui.theme import render_ask_topbar, render_sidebar_brand
from src.vector_store import load_store


@st.cache_resource(show_spinner="Loading CampusAsk index…")
def get_store():
    settings = get_settings()
    return load_store(settings.faiss_index_path, settings.metadata_path), settings


def render_sources(sources: list[dict]) -> None:
    if not sources:
        st.caption("No retrieved passages to display.")
        return
    for src in sources:
        title = html.escape(str(src.get("title") or "Untitled source"))
        loc = html.escape(str(src.get("location") or ""))
        url = str(src.get("url") or "")
        excerpt = html.escape(str(src.get("excerpt") or ""))
        level = html.escape(str(src.get("level") or ""))
        year = html.escape(str(src.get("year") or ""))
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
              <div class="source-meta">{loc} · Level: {level} · Year: {year} · {link}</div>
              <div>{excerpt}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_ask_sidebar() -> str:
    with st.sidebar:
        render_sidebar_brand()
        st.markdown("---")
        level = st.selectbox(
            "Academic level",
            options=["All", "Undergraduate", "Graduate"],
            index=0,
            help="Filters retrieval toward matching catalog level when metadata allows.",
        )
        if st.button("New conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        if st.button("Back to home", use_container_width=True, type="secondary"):
            st.switch_page("app.py")
    return level


def render_ask_experience() -> None:
    """Polished grounded chat UI (RAG behavior unchanged)."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    level = render_ask_sidebar()
    render_ask_topbar()

    try:
        store, settings = get_store()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:  # noqa: BLE001
        st.error("Could not load the CampusAsk index. Rebuild with scripts/build_index.py.")
        st.caption(str(exc))
        st.stop()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            status = message.get("status")
            if message["role"] == "assistant" and status:
                if status == "answered":
                    st.markdown(
                        '<p class="status-ok">Grounded answer</p>',
                        unsafe_allow_html=True,
                    )
                elif status == "abstained":
                    st.markdown(
                        '<p class="status-abstain">Abstention — evidence insufficient</p>',
                        unsafe_allow_html=True,
                    )
                elif status == "error":
                    st.markdown(
                        '<p class="status-err">Generation error</p>',
                        unsafe_allow_html=True,
                    )
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("Sources & evidence", expanded=False):
                    render_sources(message["sources"])

    prompt = st.chat_input("Ask a UCM policy question…")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    level_map = {
        "All": "all",
        "Undergraduate": "undergraduate",
        "Graduate": "graduate",
    }
    with st.chat_message("assistant"):
        with st.spinner("Retrieving evidence and drafting a grounded answer…"):
            result = answer_question(
                prompt,
                store=store,
                settings=settings,
                academic_level=level_map[level],
            )

        if result.status == "answered":
            st.markdown(
                '<p class="status-ok">Grounded answer</p>',
                unsafe_allow_html=True,
            )
        elif result.status == "abstained":
            st.markdown(
                '<p class="status-abstain">Abstention — evidence insufficient</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p class="status-err">Generation error</p>',
                unsafe_allow_html=True,
            )

        st.markdown(result.answer)
        with st.expander("Sources & evidence", expanded=result.status == "answered"):
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
            "sources": result.sources,
            "status": result.status,
        }
    )
