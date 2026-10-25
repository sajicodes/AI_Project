"""CampusAsk — UCM-branded landing for grounded policy Q&A."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.theme import inject_theme, render_landing_copy, render_landing_footnote

st.set_page_config(
    page_title="CampusAsk | University of Central Missouri",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_theme(include_hero=True)


def main() -> None:
    render_landing_copy()
    if st.button("Ask CampusAsk", type="primary", key="landing_cta"):
        st.switch_page("pages/ask.py")
    render_landing_footnote()


if __name__ == "__main__":
    main()
