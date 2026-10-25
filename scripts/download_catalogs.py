#!/usr/bin/env python3
"""Download official UCM catalog PDFs listed in data/raw/sources.json.

The 2026–2027 undergraduate and graduate catalogs are committed under
data/raw/catalogs/. Use this script to refresh from the publisher or to
restore the files if they are missing locally.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "data" / "raw" / "sources.json"
USER_AGENT = "CampusAsk/1.0 (academic research; contact via GitHub)"


def _is_pdf(path: Path) -> bool:
    try:
        return path.read_bytes()[:5] == b"%PDF-"
    except OSError:
        return False


def download_pdf(url: str, dest: Path, *, force: bool = False, timeout: int = 120) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force and _is_pdf(dest):
        print(f"skip (exists): {dest} ({dest.stat().st_size} bytes)")
        return dest

    print(f"download: {url}")
    print(f"      -> {dest}")
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
        stream=True,
    )
    response.raise_for_status()
    content_type = (response.headers.get("Content-Type") or "").lower()
    data = response.content
    if not data.startswith(b"%PDF-"):
        raise RuntimeError(
            f"Response is not a PDF (Content-Type={content_type!r}, "
            f"magic={data[:16]!r}). Refusing to write {dest}."
        )
    dest.write_bytes(data)
    print(f"wrote {dest.stat().st_size} bytes")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Download UCM catalog PDFs from sources.json")
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Path to sources.json",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if a valid local PDF already exists",
    )
    args = parser.parse_args()

    raw_dir = ROOT / "data" / "raw"
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    pdf_sources = [
        s
        for s in registry.get("sources", [])
        if s.get("enabled", True)
        and str(s.get("content_type", "")).lower() == "pdf"
        and s.get("local_path")
        and s.get("url")
    ]
    if not pdf_sources:
        print("No enabled PDF sources with url + local_path found.", file=sys.stderr)
        return 1

    ok = 0
    for source in pdf_sources:
        dest = Path(source["local_path"])
        if not dest.is_absolute():
            dest = raw_dir / dest
        try:
            download_pdf(source["url"], dest, force=args.force)
            ok += 1
            print(f"ok: {source['source_id']}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED {source['source_id']}: {exc}", file=sys.stderr)
            return 1

    print(f"Downloaded/verified {ok} PDF source(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
