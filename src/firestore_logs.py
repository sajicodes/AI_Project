"""Firestore helpers for CampusAsk check-in / login logs.

Uses Firebase Admin on the API host so service-account credentials stay
server-side. When Firebase is not configured, logging is a no-op so check-in
still works locally without a project.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("campusask.firestore")

STUDENTS_COLLECTION = "students"
LOGIN_LOGS_COLLECTION = "login_logs"

# Seedable demo roster (realistic names + 700-prefixed 9-digit UCM IDs).
DUMMY_STUDENTS: list[dict[str, str]] = [
    {
        "full_name": "Sajitha Konda",
        "ucm_id": "700782694",
        "academic_level": "graduate",
    },
    {
        "full_name": "Alex Rivera",
        "ucm_id": "700012345",
        "academic_level": "undergraduate",
    },
    {
        "full_name": "Priya Nair",
        "ucm_id": "700445821",
        "academic_level": "graduate",
    },
    {
        "full_name": "Marcus Chen",
        "ucm_id": "700198376",
        "academic_level": "undergraduate",
    },
    {
        "full_name": "Jordan Blake",
        "ucm_id": "700556019",
        "academic_level": "undergraduate",
    },
    {
        "full_name": "Amelia Soto",
        "ucm_id": "700334870",
        "academic_level": "graduate",
    },
    {
        "full_name": "Noah Patel",
        "ucm_id": "700667142",
        "academic_level": "undergraduate",
    },
    {
        "full_name": "Elena Vargas",
        "ucm_id": "700221908",
        "academic_level": "graduate",
    },
    {
        "full_name": "Chris Okonkwo",
        "ucm_id": "700809533",
        "academic_level": "undergraduate",
    },
    {
        "full_name": "Mia Thompson",
        "ucm_id": "700473266",
        "academic_level": "undergraduate",
    },
]

_app = None
_init_attempted = False


def firebase_enabled() -> bool:
    """True when env asks for Firebase and credentials look present."""
    flag = os.getenv("FIREBASE_ENABLED", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return _credentials_available()
    # Auto-enable when credentials are configured.
    return _credentials_available()


def _credentials_available() -> bool:
    if os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip():
        return True
    path = (
        os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )
    return bool(path and Path(path).is_file())


def _project_id() -> str | None:
    return (
        os.getenv("FIREBASE_PROJECT_ID", "").strip()
        or os.getenv("GCLOUD_PROJECT", "").strip()
        or None
    )


def get_firestore_client():
    """Return a Firestore client, or None when Firebase is unavailable."""
    global _app, _init_attempted
    if not firebase_enabled():
        return None
    if _init_attempted and _app is None:
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        logger.warning("firebase-admin is not installed; skipping Firestore logging")
        _init_attempted = True
        return None

    if _app is None:
        _init_attempted = True
        try:
            existing = firebase_admin._apps  # type: ignore[attr-defined]
            if existing:
                _app = next(iter(existing.values()))
            else:
                cred = _load_credentials(credentials)
                options: dict[str, Any] = {}
                project = _project_id()
                if project:
                    options["projectId"] = project
                _app = firebase_admin.initialize_app(cred, options or None)
            logger.info("Firebase Admin initialized for CampusAsk login logs")
        except Exception:  # noqa: BLE001
            logger.exception("Failed to initialize Firebase Admin")
            _app = None
            return None

    try:
        return firestore.client(app=_app)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to create Firestore client")
        return None


def _load_credentials(credentials_module: Any) -> Any:
    raw_json = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
    if raw_json:
        info = json.loads(raw_json)
        return credentials_module.Certificate(info)

    path = (
        os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )
    if not path:
        raise RuntimeError(
            "Set FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH "
            "(or GOOGLE_APPLICATION_CREDENTIALS)."
        )
    return credentials_module.Certificate(path)


def log_checkin(
    *,
    full_name: str,
    ucm_id: str,
    academic_level: str | None = None,
    user_agent: str | None = None,
) -> str | None:
    """Write one successful check-in to ``login_logs``. Returns doc id or None."""
    db = get_firestore_client()
    if db is None:
        return None

    from google.cloud.firestore import SERVER_TIMESTAMP

    payload: dict[str, Any] = {
        "full_name": full_name,
        "ucm_id": ucm_id,
        "timestamp": SERVER_TIMESTAMP,
        "created_at_iso": datetime.now(timezone.utc).isoformat(),
    }
    if academic_level:
        payload["academic_level"] = academic_level
    if user_agent:
        payload["user_agent"] = user_agent[:500]

    try:
        _update_time, doc_ref = db.collection(LOGIN_LOGS_COLLECTION).add(payload)
        logger.info("Logged check-in for student ending …%s", ucm_id[-4:])
        return doc_ref.id
    except Exception:  # noqa: BLE001
        # Never fail the check-in UX if Firestore is down.
        logger.exception("Failed to write check-in login log")
        return None


def list_login_logs(limit: int = 25) -> list[dict[str, Any]]:
    """Return recent login logs (newest first). Empty when Firebase is off."""
    db = get_firestore_client()
    if db is None:
        return []

    limit = max(1, min(int(limit), 100))
    try:
        from google.cloud.firestore import Query

        query = (
            db.collection(LOGIN_LOGS_COLLECTION)
            .order_by("timestamp", direction=Query.DESCENDING)
            .limit(limit)
        )
        rows: list[dict[str, Any]] = []
        for snap in query.stream():
            data = snap.to_dict() or {}
            ts = data.get("timestamp")
            if hasattr(ts, "isoformat"):
                data["timestamp"] = ts.isoformat()
            elif ts is not None:
                data["timestamp"] = str(ts)
            data["id"] = snap.id
            rows.append(data)
        return rows
    except Exception:  # noqa: BLE001
        logger.exception("Failed to list login logs")
        return []


def seed_students(students: list[dict[str, str]] | None = None) -> int:
    """Upsert dummy students into the ``students`` collection. Returns count."""
    db = get_firestore_client()
    if db is None:
        raise RuntimeError(
            "Firebase is not configured. Set FIREBASE_PROJECT_ID and "
            "FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH."
        )

    roster = students or DUMMY_STUDENTS
    written = 0
    for student in roster:
        ucm_id = student["ucm_id"]
        doc = {
            "full_name": student["full_name"],
            "ucm_id": ucm_id,
            "academic_level": student.get("academic_level") or "undergraduate",
            "seeded": True,
            "updated_at_iso": datetime.now(timezone.utc).isoformat(),
        }
        db.collection(STUDENTS_COLLECTION).document(ucm_id).set(doc, merge=True)
        written += 1
    return written


def seed_sample_login_logs(count: int = 3) -> int:
    """Write a few sample login logs from the dummy roster for demos."""
    roster = DUMMY_STUDENTS[: max(0, min(count, len(DUMMY_STUDENTS)))]
    written = 0
    for student in roster:
        doc_id = log_checkin(
            full_name=student["full_name"],
            ucm_id=student["ucm_id"],
            academic_level=student.get("academic_level"),
            user_agent="CampusAsk seed script",
        )
        if doc_id:
            written += 1
    return written
