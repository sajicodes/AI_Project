"""CampusAsk grounded Q&A experience."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.chat import render_ask_experience
from src.ui.theme import inject_theme

st.set_page_config(
    page_title="Ask | CampusAsk | UCM",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()
render_ask_experience()
