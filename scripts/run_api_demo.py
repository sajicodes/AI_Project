"""Local API launcher with optional stubbed LLM for UI demos without a key.

Usage:
  python3 scripts/run_api_demo.py            # normal (needs LLM_API_KEY for answers)
  python3 scripts/run_api_demo.py --stub-llm # stub grounded answers from real retrieval
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _stub_llm(prompt: str, settings) -> str:  # noqa: ARG001
    """Return a short grounded reply citing a real evidence CHUNK_ID from the prompt."""
    import re

    blocks = re.split(r"\n---\n", prompt)
    preferred = None
    fallback = None
    for block in blocks:
        m = re.search(r"CHUNK_ID:\s*(\S+)", block)
        if not m:
            continue
        chunk_id = m.group(1)
        if fallback is None:
            fallback = chunk_id
        if "fixture" not in chunk_id.lower():
            preferred = chunk_id
            break
    cite = preferred or fallback or "unknown"
    return (
        "Based on the indexed UCM catalogs, undergraduate academic probation is "
        "defined by the GPA thresholds in the retrieved catalog evidence "
        f"[cite:{cite}]. Review the cited Undergraduate Catalog pages for the "
        "exact rule that applies to your situation."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--stub-llm",
        action="store_true",
        help="Stub LLM generation using real retrieval + citation IDs (demo only).",
    )
    args = parser.parse_args()

    import uvicorn

    if args.stub_llm:
        with patch("src.generation._call_llm", side_effect=_stub_llm):
            uvicorn.run("api.main:app", host=args.host, port=args.port, reload=False)
    else:
        uvicorn.run("api.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
