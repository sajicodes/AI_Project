"""Allowlist ingestion from local fixture files (no network)."""

from pathlib import Path

from src.ingestion import ingest_all, load_sources_registry

ROOT = Path(__file__).resolve().parents[1]


def test_load_sources_registry():
    sources = load_sources_registry(ROOT / "data" / "raw" / "sources.json")
    assert sources
    assert any(s.source_id.startswith("fixture_") for s in sources)


def test_ingest_local_fixtures_only(tmp_path):
    # Build a fixtures-only registry to avoid network fetches of live UCM pages.
    registry = {
        "sources": [
            {
                "source_id": "fixture_policy_handbook",
                "title": "[DEV FIXTURE] Sample Policy Handbook",
                "url": "https://example.invalid/fixture-handbook",
                "year": "2024-2025",
                "level": "all",
                "content_type": "html",
                "local_path": "fixtures/sample_handbook.html",
                "enabled": True,
            }
        ]
    }
    import json

    reg_path = tmp_path / "sources.json"
    reg_path.write_text(json.dumps(registry), encoding="utf-8")
    pages, log = ingest_all(reg_path, ROOT / "data" / "raw")
    assert pages
    assert any("grade replacement" in p.text.lower() for p in pages)
    assert log["total_pages"] >= 1
