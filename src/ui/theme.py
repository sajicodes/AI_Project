"""UCM-branded theme injection and chrome HTML for CampusAsk."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
_STYLES_PATH = _ROOT / "styles" / "campusask.css"
_MULE_HERO = _ROOT / "assets" / "mule-silhouette.svg"
_MULE_MARK = _ROOT / "assets" / "mule-mark.svg"

CAPTION = "Official UCM policy answers, grounded in the catalogs."


def _svg_inline(path: Path, *, css_class: str) -> str:
    """Inline an original asset SVG with a CSS class (strip XML declaration)."""
    raw = path.read_text(encoding="utf-8")
    raw = raw.replace('<?xml version="1.0" encoding="UTF-8"?>', "").strip()
    if raw.startswith("<svg"):
        raw = raw.replace("<svg", f'<svg class="{css_class}"', 1)
    return raw


def inject_theme() -> None:
    """Load CampusAsk CSS into the Streamlit page."""
    css = _STYLES_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_landing_copy() -> None:
    """Hero brand copy + dominant mule visual (one composition; CTA is Streamlit)."""
    mule = _svg_inline(_MULE_HERO, css_class="mule-hero-svg")
    st.markdown('<div class="landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="landing-stage">
          <div class="landing-copy">
            <div class="landing-gold-rule" aria-hidden="true"></div>
            <p class="landing-mules">Missouri Mules</p>
            <h1 class="landing-brand">University of<br>Central Missouri</h1>
            <p class="landing-product">CampusAsk</p>
            <p class="landing-headline">{CAPTION}</p>
            <p class="landing-support">
              Every reply cites official catalog evidence—or clearly abstains.
            </p>
          </div>
          <div class="landing-mule" aria-hidden="true">
            {mule}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_landing_footnote() -> None:
    st.markdown(
        """
        <p class="landing-footnote">
          Indexed Undergraduate &amp; Graduate Catalogs and Registrar guidance.
        </p>
        """,
        unsafe_allow_html=True,
    )


def render_ask_topbar() -> None:
    """Official CampusAsk chrome with mule mark and professional caption."""
    mark = _svg_inline(_MULE_MARK, css_class="mule-mark-svg")
    st.markdown(
        f"""
        <div class="ask-topbar">
          <div class="ask-mark" aria-hidden="true">{mark}</div>
          <div class="ask-brand-block">
            <p class="ask-uni">University of Central Missouri · Missouri Mules</p>
            <p class="ask-title">CampusAsk</p>
            <p class="ask-tag">{CAPTION}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    """Sidebar brand lockup — CampusAsk first, with mule mark."""
    mark = _svg_inline(_MULE_MARK, css_class="mule-mark-svg mule-mark-sidebar")
    st.markdown(
        f"""
        <div class="sidebar-lockup">
          <div class="sidebar-mark" aria-hidden="true">{mark}</div>
          <div>
            <p class="sidebar-uni">University of Central Missouri</p>
            <p class="sidebar-brand">CampusAsk</p>
            <p class="sidebar-mules">Missouri Mules</p>
            <p class="sidebar-tag">{CAPTION}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
