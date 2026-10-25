"""CampusAsk — Streamlit product UI for grounded UCM policy Q&A."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import get_settings
from src.generation import answer_question
from src.vector_store import load_store

st.set_page_config(
    page_title="CampusAsk",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

:root {
  --ink: #1a1520;
  --muted: #5c5566;
  --paper: #f7f3ee;
  --panel: #ffffff;
  --accent: #9b1c2c;
  --accent-deep: #6f101c;
  --line: #e4ddd3;
  --ok: #1f6b4a;
  --warn: #8a5a00;
}

html, body, [class*="css"] {
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
  color: var(--ink);
}

.stApp {
  background:
    radial-gradient(1200px 500px at 10% -10%, #f0e2d8 0%, transparent 55%),
    radial-gradient(900px 420px at 100% 0%, #e8efe9 0%, transparent 50%),
    linear-gradient(180deg, #fbf8f4 0%, #f3eee7 100%);
}

.block-container {
  padding-top: 1.4rem;
  padding-bottom: 3rem;
  max-width: 1100px;
}

.campus-hero {
  padding: 1.25rem 1.5rem 1.4rem;
  border-bottom: 1px solid var(--line);
  margin-bottom: 1rem;
}
.campus-brand {
  font-family: Fraunces, Georgia, serif;
  font-size: 2.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--accent-deep);
  line-height: 1.1;
  margin: 0;
}
.campus-tag {
  margin: 0.45rem 0 0;
  color: var(--muted);
  font-size: 1.05rem;
  max-width: 38rem;
}
.campus-pill {
  display: inline-block;
  margin-top: 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--accent);
}

.stChatMessage {
  background: transparent;
}
div[data-testid="stChatMessageContent"] {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 0.85rem 1rem;
}

.source-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.65rem;
}
.source-card h4 {
  margin: 0 0 0.25rem;
  font-size: 0.98rem;
}
.source-meta {
  color: var(--muted);
  font-size: 0.85rem;
  margin-bottom: 0.45rem;
}
.status-ok { color: var(--ok); font-weight: 600; }
.status-abstain { color: var(--warn); font-weight: 600; }
.status-err { color: var(--accent); font-weight: 600; }
"""

st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading CampusAsk index…")
def get_store():
    settings = get_settings()
    return load_store(settings.faiss_index_path, settings.metadata_path), settings


def render_sources(sources: list[dict]) -> None:
    if not sources:
        st.caption("No retrieved passages to display.")
        return
    for src in sources:
        title = src.get("title") or "Untitled source"
        loc = src.get("location") or ""
        url = src.get("url") or ""
        excerpt = src.get("excerpt") or ""
        level = src.get("level") or ""
        year = src.get("year") or ""
        link = f'<a href="{url}" target="_blank" rel="noopener">Open source</a>' if url else ""
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


def main() -> None:
    st.markdown(
        """
        <div class="campus-hero">
          <p class="campus-pill">University of Central Missouri</p>
          <h1 class="campus-brand">CampusAsk</h1>
          <p class="campus-tag">
            Ask natural-language questions about official UCM academic policies.
            Answers are grounded in retrieved catalog, handbook, and Registrar text —
            with citations, or a clear abstention when evidence is missing.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.subheader("Session")
        level = st.selectbox(
            "Academic level",
            options=["All", "Undergraduate", "Graduate"],
            index=0,
            help="Filters retrieval toward matching catalog level when metadata allows.",
        )
        if st.button("Reset chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.markdown("---")
        st.markdown(
            "**Principles**  \n"
            "• Grounding — retrieved text only  \n"
            "• Citation — document + page/section  \n"
            "• Abstention — no guessing"
        )
        st.caption(
            "Requires a built FAISS index (`python scripts/build_index.py`) "
            "and `LLM_API_KEY` in `.env` for answer generation."
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

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
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("Sources", expanded=False):
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
                f'<p class="status-ok">Grounded answer</p>',
                unsafe_allow_html=True,
            )
        elif result.status == "abstained":
            st.markdown(
                f'<p class="status-abstain">Abstention — evidence insufficient</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<p class="status-err">Generation error</p>',
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


if __name__ == "__main__":
    main()
