"""Streamlit session wrappers for student identity (legacy Streamlit UI).

Core validation lives in ``src.identity`` so the FastAPI + Next.js path
can reuse it without importing Streamlit.
"""

from __future__ import annotations

import streamlit as st

from src.identity import (
    StudentIdentity,
    build_identity,
    normalize_ucm_id,
    validate_full_name,
    validate_ucm_id,
    welcome_greeting,
)

SESSION_NAME_KEY = "student_full_name"
SESSION_ID_KEY = "student_ucm_id"
SESSION_GREETED_KEY = "student_greeted"

__all__ = [
    "SESSION_GREETED_KEY",
    "SESSION_ID_KEY",
    "SESSION_NAME_KEY",
    "StudentIdentity",
    "build_identity",
    "clear_identity",
    "consume_greeting",
    "get_identity",
    "identity_is_set",
    "normalize_ucm_id",
    "render_identity_gate",
    "set_identity",
    "validate_full_name",
    "validate_ucm_id",
    "welcome_greeting",
]


def get_identity() -> StudentIdentity | None:
    name = st.session_state.get(SESSION_NAME_KEY)
    ucm_id = st.session_state.get(SESSION_ID_KEY)
    if not name or not ucm_id:
        return None
    return StudentIdentity(full_name=str(name), ucm_id=str(ucm_id))


def identity_is_set() -> bool:
    return get_identity() is not None


def clear_identity() -> None:
    for key in (SESSION_NAME_KEY, SESSION_ID_KEY, SESSION_GREETED_KEY, "messages"):
        if key in st.session_state:
            del st.session_state[key]


def set_identity(full_name: str, ucm_id: str) -> StudentIdentity:
    identity = build_identity(full_name, ucm_id)
    st.session_state[SESSION_NAME_KEY] = identity.full_name
    st.session_state[SESSION_ID_KEY] = identity.ucm_id
    st.session_state[SESSION_GREETED_KEY] = False
    st.session_state.messages = []
    return identity


def consume_greeting() -> str | None:
    """Return a one-time greeting after identity submit; then mark as shown."""
    identity = get_identity()
    if identity is None:
        return None
    if st.session_state.get(SESSION_GREETED_KEY):
        return None
    st.session_state[SESSION_GREETED_KEY] = True
    return welcome_greeting(identity.first_name)


def render_identity_gate() -> bool:
    """Render the identity form. Returns True when identity is already set."""
    if identity_is_set():
        return True

    st.markdown(
        """
        <div class="identity-panel">
          <p class="identity-eyebrow">Academic Catalog Desk</p>
          <h2 class="identity-title">Student check-in</h2>
          <p class="identity-copy">
            Enter your name and UCM ID to start. Your ID stays in this browser
            session only—it is never sent to the language model.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("student_identity_form", clear_on_submit=False):
        name = st.text_input(
            "Full name",
            placeholder="e.g. Alex Rivera",
            max_chars=80,
        )
        ucm_id = st.text_input(
            "UCM ID number",
            placeholder="e.g. 700782694",
            max_chars=12,
            help="Nine digits starting with 700. Stored in session state for this visit—not logged or sent to the LLM.",
        )
        submitted = st.form_submit_button(
            "Continue to CampusAsk", type="primary", use_container_width=True
        )

    if submitted:
        name_err = validate_full_name(name)
        id_err = validate_ucm_id(ucm_id)
        if name_err or id_err:
            if name_err:
                st.error(name_err)
            if id_err:
                st.error(id_err)
            return False
        set_identity(name, ucm_id)
        st.rerun()

    return False
