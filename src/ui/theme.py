"""UCM-branded theme injection and chrome HTML for CampusAsk."""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
_STYLES_PATH = _ROOT / "styles" / "campusask.css"
_UCM = _ROOT / "assets" / "ucm"

CAPTION = "Official UCM policy answers, grounded in the catalogs."


@lru_cache(maxsize=1)
def _cached_css_shell() -> str:
    """Base stylesheet without the heavy hero image (Ask pages stay light)."""
    return _STYLES_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=4)
def _data_uri(path_str: str, mime: str) -> str:
    payload = base64.b64encode(Path(path_str).read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def _logo_uri() -> str:
    return _data_uri(str(_UCM / "ucm-logo.webp"), "image/webp")


def _mo_uri() -> str:
    return _data_uri(str(_UCM / "mo-the-mule.webp"), "image/webp")


def _quad_uri() -> str:
    return _data_uri(str(_UCM / "campus-quad.webp"), "image/webp")


def inject_theme(*, include_hero: bool = False) -> None:
    """Inject CampusAsk CSS. Hero campus photo only when include_hero=True (landing)."""
    css = _cached_css_shell()
    if include_hero:
        css = css.replace("/*__UCM_QUAD_URI__*/", _quad_uri())
    else:
        # Keep var valid without shipping the quad payload on Ask.
        css = css.replace(
            '--ucm-quad: url("/*__UCM_QUAD_URI__*/");',
            "--ucm-quad: none;",
        )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_landing_copy() -> None:
    """Full-bleed campus hero with official crest + CampusAsk brand copy."""
    logo = _logo_uri()
    st.markdown('<div class="landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="landing-stage">
          <div class="landing-copy">
            <img class="landing-logo" src="{logo}" alt="University of Central Missouri" width="340" height="178" />
            <p class="landing-mules">Academic Catalog Desk</p>
            <p class="landing-product">CampusAsk</p>
            <p class="landing-headline">{CAPTION}</p>
            <p class="landing-support">
              Every reply cites official catalog evidence—or clearly abstains.
            </p>
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
    """Official CampusAsk chrome with UCM crest lockup."""
    logo = _logo_uri()
    st.markdown(
        f"""
        <div class="ask-topbar">
          <img class="ask-logo" src="{logo}" alt="University of Central Missouri" width="220" height="115" />
          <div class="ask-brand-block">
            <p class="ask-uni">Academic Catalog Desk</p>
            <p class="ask-title">CampusAsk</p>
            <p class="ask-tag">{CAPTION}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    """Sidebar brand lockup with official UCM crest."""
    logo = _logo_uri()
    st.markdown(
        f"""
        <div class="sidebar-lockup">
          <img class="sidebar-logo" src="{logo}" alt="University of Central Missouri" width="210" height="110" />
          <div>
            <p class="sidebar-brand">CampusAsk</p>
            <p class="sidebar-mules">Academic Catalog Desk</p>
            <p class="sidebar-tag">{CAPTION}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ask_empty_state() -> None:
    """Quiet Mo the Mule empty-state when the conversation is new."""
    mo = _mo_uri()
    st.markdown(
        f"""
        <div class="ask-empty">
          <img class="ask-empty-mo" src="{mo}" alt="Mo the Mule studying in the library" width="480" height="319" />
          <div class="ask-empty-copy">
            <p class="ask-empty-title">Ask CampusAsk</p>
            <p class="ask-empty-text">{CAPTION}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
