"""Firestore check-in log helpers (mocked; no real Firebase credentials required)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.firestore_logs import DUMMY_STUDENTS, firebase_enabled, log_checkin


def test_dummy_students_are_700_nine_digit():
    assert 8 <= len(DUMMY_STUDENTS) <= 12
    assert any(
        s["full_name"].startswith("Sajitha") and s["ucm_id"] == "700782694"
        for s in DUMMY_STUDENTS
    )
    for student in DUMMY_STUDENTS:
        assert student["ucm_id"].isdigit()
        assert len(student["ucm_id"]) == 9
        assert student["ucm_id"].startswith("700")
        assert student["full_name"].strip()


def test_firebase_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("FIREBASE_ENABLED", raising=False)
    monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
    monkeypatch.delenv("FIREBASE_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    assert firebase_enabled() is False
    assert log_checkin(full_name="Alex Rivera", ucm_id="700012345") is None


def test_log_checkin_writes_when_client_available(monkeypatch):
    monkeypatch.setenv("FIREBASE_ENABLED", "true")
    monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", '{"type":"service_account"}')

    mock_doc = MagicMock()
    mock_doc.id = "log-abc"
    mock_collection = MagicMock()
    mock_collection.add.return_value = (None, mock_doc)
    mock_db = MagicMock()
    mock_db.collection.return_value = mock_collection

    with patch("src.firestore_logs.get_firestore_client", return_value=mock_db):
        doc_id = log_checkin(
            full_name="Sajitha Konda",
            ucm_id="700782694",
            academic_level="graduate",
            user_agent="pytest",
        )

    assert doc_id == "log-abc"
    mock_db.collection.assert_called_with("login_logs")
    args, _kwargs = mock_collection.add.call_args
    payload = args[0]
    assert payload["full_name"] == "Sajitha Konda"
    assert payload["ucm_id"] == "700782694"
    assert payload["academic_level"] == "graduate"
    assert payload["user_agent"] == "pytest"
