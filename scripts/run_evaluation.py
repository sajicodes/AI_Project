#!/usr/bin/env python3
"""Run the CampusAsk evaluation harness against the benchmark file."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import get_settings
from src.evaluation import run_evaluation

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CampusAsk evaluation harness")
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=None,
        help="Benchmark JSON (default: data/benchmark/questions.json)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Results directory (default: results/)",
    )
    args = parser.parse_args()
    settings = get_settings()
    benchmark = args.benchmark or (settings.data_benchmark / "questions.json")
    if not benchmark.exists():
        print(f"Benchmark not found: {benchmark}", file=sys.stderr)
        return 1
    if not settings.faiss_index_path.exists():
        print(
            "FAISS index missing. Run: python scripts/build_index.py",
            file=sys.stderr,
        )
        return 1

    summary = run_evaluation(
        benchmark,
        settings=settings,
        out_dir=args.out_dir or settings.results_dir,
    )
    print(
        json.dumps(
            {
                "n_questions": summary["benchmark"]["n_questions"],
                "n_verified": summary["benchmark"]["n_verified"],
                "ready_for_scored_reporting": summary["benchmark"][
                    "ready_for_scored_reporting"
                ],
                "aggregate": summary["aggregate"],
                "output": str((args.out_dir or settings.results_dir) / "evaluation_run.json"),
            },
            indent=2,
        )
    )
    if not summary["benchmark"]["ready_for_scored_reporting"]:
        print(
            "\nNote: Gold answers are not fully human-verified. "
            "Aggregate accuracy/hallucination remain null by design.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
