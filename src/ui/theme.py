"""UCM-branded theme injection and chrome HTML for CampusAsk."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
_STYLES_PATH = _ROOT / "styles" / "campusask.css"
_UCM = _ROOT / "assets" / "ucm"

CAPTION = "Official UCM policy answers, grounded in the catalogs."


def _data_uri(path: Path, mime: str) -> str:
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def _asset_uris() -> dict[str, str]:
    return {
        "quad": _data_uri(_UCM / "campus-quad.webp", "image/webp"),
        "logo": _data_uri(_UCM / "ucm-logo.jpg", "image/jpeg"),
        "mo": _data_uri(_UCM / "mo-the-mule.webp", "image/webp"),
    }


def inject_theme() -> None:
    """Load CampusAsk CSS, including official UCM imagery as data URIs."""
    css = _STYLES_PATH.read_text(encoding="utf-8")
    uris = _asset_uris()
    css = css.replace("/*__UCM_QUAD_URI__*/", uris["quad"])
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.session_state["_ucm_logo_uri"] = uris["logo"]
    st.session_state["_ucm_mo_uri"] = uris["mo"]


def _logo_uri() -> str:
    if "_ucm_logo_uri" not in st.session_state:
        st.session_state["_ucm_logo_uri"] = _asset_uris()["logo"]
    return st.session_state["_ucm_logo_uri"]


def _mo_uri() -> str:
    if "_ucm_mo_uri" not in st.session_state:
        st.session_state["_ucm_mo_uri"] = _asset_uris()["mo"]
    return st.session_state["_ucm_mo_uri"]


def render_landing_copy() -> None:
    """Full-bleed campus hero with official crest + CampusAsk brand copy."""
    logo = _logo_uri()
    st.markdown('<div class="landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="landing-stage">
          <div class="landing-copy">
            <img class="landing-logo" src="{logo}" alt="University of Central Missouri" />
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
          <img class="ask-logo" src="{logo}" alt="University of Central Missouri" />
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
          <img class="sidebar-logo" src="{logo}" alt="University of Central Missouri" />
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
          <img class="ask-empty-mo" src="{mo}" alt="Mo the Mule studying in the library" />
          <div class="ask-empty-copy">
            <p class="ask-empty-title">Ask CampusAsk</p>
            <p class="ask-empty-text">{CAPTION}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
