"""Minimal FastAPI smoke tests (no LLM required)."""

from __future__ import annotations

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
    res = client.post(
        "/v1/identity/validate",
        json={"full_name": "Alex Rivera", "ucm_id": "700012345"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["first_name"] == "Alex"
    assert body["masked_id"].endswith("2345")
    assert "Hi Alex" in (body["greeting"] or "")


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


def test_identity_rejects_non_700_id():
    res = client.post(
        "/v1/identity/validate",
        json={"full_name": "Alex Rivera", "ucm_id": "123456789"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert "ucm_id" in body["errors"]
    assert "700" in body["errors"]["ucm_id"]
