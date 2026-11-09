"""Minimal FastAPI smoke tests (no LLM required)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "campusask-api"


def test_samples():
    res = client.get("/v1/samples")
    assert res.status_code == 200
    samples = res.json()["samples"]
    assert len(samples) >= 3
    assert samples[0]["id"]


def test_identity_validate_ok():
    with patch("api.main.log_checkin", return_value="log-1") as mock_log:
        res = client.post(
            "/v1/identity/validate",
            json={
                "full_name": "Alex Rivera",
                "ucm_id": "700012345",
                "academic_level": "undergraduate",
                "user_agent": "pytest-agent",
            },
        )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["first_name"] == "Alex"
    assert body["masked_id"].endswith("2345")
    assert "Hi Alex" in (body["greeting"] or "")
    mock_log.assert_called_once()
    kwargs = mock_log.call_args.kwargs
    assert kwargs["full_name"] == "Alex Rivera"
    assert kwargs["ucm_id"] == "700012345"
    assert kwargs["academic_level"] == "undergraduate"
    assert kwargs["user_agent"] == "pytest-agent"


def test_identity_validate_bad():
    res = client.post(
        "/v1/identity/validate",
        json={"full_name": "A", "ucm_id": "12"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert "full_name" in body["errors"]
    assert "ucm_id" in body["errors"]


def test_ask_greeting_never_abstains():
    res = client.post(
        "/v1/ask",
        json={"question": "HI", "academic_level": "all", "first_name": "Alex"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "conversational"
    assert body["intent"] == "greeting"
    assert "Hi Alex" in body["answer"]
    assert body["sources"] == []


def test_ask_hi_how_are_you_short_circuits():
    res = client.post(
        "/v1/ask",
        json={
            "question": "Hi how are you",
            "academic_level": "all",
            "first_name": "Alex",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "conversational"
    assert body["intent"] == "how_are_you"
    assert "Alex" in body["answer"]
    assert body["sources"] == []


def test_ask_masters_student_context_never_abstains():
    res = client.post(
        "/v1/ask",
        json={
            "question": "i am a masters student",
            "academic_level": "all",
            "first_name": "Alex",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "conversational"
    assert body["intent"] == "student_context"
    assert "master" in body["answer"].lower()
    assert body["sources"] == []
    assert body.get("suggested_academic_level") == "graduate"
    assert body.get("academic_level") == "graduate"


def test_ask_masters_cs_with_undergraduate_level_never_abstains():
    """Undergraduate UI + masters CS identity must not return abstained."""
    from unittest.mock import patch

    def fake_llm(prompt: str, _settings):
        blocks = prompt.split("CHUNK_ID: ")[1:]
        for block in blocks:
            cid_line, _, rest = block.partition("\n")
            if "Computer Science, MS" in rest or "53-976" in rest:
                return (
                    "The Computer Science MS (53-976) is a 30-hour graduate program. "
                    f"[cite:{cid_line.strip()}]"
                )
        return "ABSTAIN"

    with patch("src.generation._call_llm", side_effect=fake_llm):
        res = client.post(
            "/v1/ask",
            json={
                "question": "I am a Masters student in computer science",
                "academic_level": "undergraduate",
                "first_name": "Alex",
            },
        )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] != "abstained"
    assert body.get("suggested_academic_level") == "graduate"
    assert body.get("academic_level") == "graduate"
    assert "computer science" in body["answer"].lower() or "master" in body["answer"].lower()


def test_identity_rejects_non_700_id():
    with patch("api.main.log_checkin") as mock_log:
        res = client.post(
            "/v1/identity/validate",
            json={"full_name": "Alex Rivera", "ucm_id": "123456789"},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert "ucm_id" in body["errors"]
    assert "700" in body["errors"]["ucm_id"]
    mock_log.assert_not_called()


def test_admin_login_logs_disabled_without_token(monkeypatch):
    monkeypatch.delenv("CAMPUSASK_ADMIN_TOKEN", raising=False)
    res = client.get("/v1/admin/login-logs")
    assert res.status_code == 503


def test_admin_login_logs_requires_matching_token(monkeypatch):
    monkeypatch.setenv("CAMPUSASK_ADMIN_TOKEN", "demo-secret")
    res = client.get("/v1/admin/login-logs")
    assert res.status_code == 401
    with patch("api.main.list_login_logs", return_value=[{"id": "1", "full_name": "Alex"}]):
        res_ok = client.get(
            "/v1/admin/login-logs",
            headers={"X-Admin-Token": "demo-secret"},
        )
    assert res_ok.status_code == 200
    body = res_ok.json()
    assert body["ok"] is True
    assert body["count"] == 1
    assert body["logs"][0]["full_name"] == "Alex"
