"""Student identity validation (session UX only).

UCM ID is never sent to the LLM, never logged, and never persisted
beyond the client session (Streamlit session_state or browser storage).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Reasonable UCM-style student IDs: 7–9 digits (leading zeros allowed).
_UCM_ID_RE = re.compile(r"^\d{7,9}$")


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
