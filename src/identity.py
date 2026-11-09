"""Student identity validation (session UX only).

UCM ID is never sent to the LLM, never logged, and never persisted
beyond the client session (Streamlit session_state or browser storage).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# UCM student IDs: nine digits starting with 700 (e.g. 700782694).
_UCM_ID_RE = re.compile(r"^700\d{6}$")


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
    if not digits.isdigit():
        return "UCM ID should contain digits only."
    if len(digits) != 9:
        return "UCM ID should be 9 digits (for example, 700782694)."
    if not digits.startswith("700"):
        return "UCM ID should start with 700 (for example, 700782694)."
    if not _UCM_ID_RE.match(digits):
        return "UCM ID should be 9 digits starting with 700."
    return None


def build_identity(full_name: str, ucm_id: str) -> StudentIdentity:
    cleaned_name = " ".join(full_name.split())
    digits = normalize_ucm_id(ucm_id)
    return StudentIdentity(full_name=cleaned_name, ucm_id=digits)


def welcome_greeting(first_name: str) -> str:
    name = (first_name or "").strip() or "there"
    return (
        f"Hi {name}! How can I help with a UCM catalog "
        f"or policy question today?"
    )
