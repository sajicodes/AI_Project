"""Session-only student identity gate for CampusAsk Ask experience.

UCM ID is UX-only: never send it to the LLM, never log it, never persist
beyond Streamlit session_state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import streamlit as st

# Reasonable UCM-style student IDs: 7–9 digits (leading zeros allowed).
_UCM_ID_RE = re.compile(r"^\d{7,9}$")

SESSION_NAME_KEY = "student_full_name"
SESSION_ID_KEY = "student_ucm_id"
SESSION_GREETED_KEY = "student_greeted"


@dataclass(frozen=True)
class StudentIdentity:
    full_name: str
    ucm_id: str

    @property
    def first_name(self) -> str:
        token = (self.full_name or "").strip().split()[0] if self.full_name else ""
        return token or "there"

    @property
    def masked_id(self) -> str:
        digits = re.sub(r"\D", "", self.ucm_id or "")
        if len(digits) < 4:
            return "••••"
        return "•" * (len(digits) - 4) + digits[-4:]


def normalize_ucm_id(raw: str) -> str:
    return re.sub(r"\D", "", (raw or "").strip())


def validate_full_name(name: str) -> str | None:
    cleaned = " ".join((name or "").split())
    if len(cleaned) < 2:
        return "Enter your full name."
    if not re.search(r"[A-Za-z]", cleaned):
        return "Name must include letters."
    if len(cleaned) > 80:
        return "Name is too long."
    return None


def validate_ucm_id(raw: str) -> str | None:
    digits = normalize_ucm_id(raw)
    if not digits:
        return "Enter your UCM ID number."
    if not _UCM_ID_RE.match(digits):
        return "UCM ID should be 7–9 digits."
    return None


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
    cleaned_name = " ".join(full_name.split())
    digits = normalize_ucm_id(ucm_id)
    st.session_state[SESSION_NAME_KEY] = cleaned_name
    st.session_state[SESSION_ID_KEY] = digits
    st.session_state[SESSION_GREETED_KEY] = False
    st.session_state.messages = []
    return StudentIdentity(full_name=cleaned_name, ucm_id=digits)


def consume_greeting() -> str | None:
    """Return a one-time greeting after identity submit; then mark as shown."""
    identity = get_identity()
    if identity is None:
        return None
    if st.session_state.get(SESSION_GREETED_KEY):
        return None
    st.session_state[SESSION_GREETED_KEY] = True
    return (
        f"Hi {identity.first_name}! How can I help with a UCM catalog "
        f"or policy question today?"
    )


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
            placeholder="7–9 digits",
            max_chars=12,
            help="Digits only. Stored in session state for this visit—not logged or sent to the LLM.",
        )
        submitted = st.form_submit_button("Continue to CampusAsk", type="primary", use_container_width=True)

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
