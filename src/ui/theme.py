"""UCM-branded theme injection and chrome HTML for CampusAsk."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_STYLES_PATH = Path(__file__).resolve().parents[2] / "styles" / "campusask.css"


def inject_theme() -> None:
    """Load CampusAsk CSS into the Streamlit page."""
    css = _STYLES_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_landing_copy() -> None:
    """Hero brand copy for the landing composition (CTA is a Streamlit button)."""
    st.markdown('<div class="landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="landing-stage">
          <div class="landing-gold-rule" aria-hidden="true"></div>
          <h1 class="landing-brand">University of<br>Central Missouri</h1>
          <p class="landing-product">CampusAsk</p>
          <p class="landing-headline">Official policy answers, grounded in campus documents.</p>
          <p class="landing-support">
            Ask about catalogs, the student handbook, and Registrar guidance—
            every reply cites evidence, or clearly abstains when it cannot.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_landing_footnote() -> None:
    st.markdown(
        """
        <p class="landing-footnote">
          Answers cite official indexed catalogs and Registrar text.
          Unsupported questions abstain.
        </p>
        """,
        unsafe_allow_html=True,
    )


def render_ask_topbar() -> None:
    """Compact brand chrome above the chat experience."""
    st.markdown(
        """
        <div class="ask-topbar">
          <div class="ask-brand-block">
            <p class="ask-uni">University of Central Missouri</p>
            <p class="ask-title">CampusAsk</p>
            <p class="ask-tag">
              Grounded answers from official UCM academic policy—with citations.
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
