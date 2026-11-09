#!/usr/bin/env python3
"""Seed Firestore with dummy UCM students and optional sample login logs.

Requires a Firebase project with Firestore enabled and service-account
credentials in the environment (see .env.example).

Usage:
  python scripts/seed_firestore.py
  python scripts/seed_firestore.py --with-login-logs
  python scripts/seed_firestore.py --login-log-count 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from src.firestore_logs import (  # noqa: E402
    DUMMY_STUDENTS,
    firebase_enabled,
    seed_sample_login_logs,
    seed_students,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed CampusAsk Firestore students (+ optional login logs)."
    )
    parser.add_argument(
        "--with-login-logs",
        action="store_true",
        help="Also write a few sample check-in / login log documents.",
    )
    parser.add_argument(
        "--login-log-count",
        type=int,
        default=3,
        help="How many sample login logs to write when --with-login-logs is set.",
    )
    args = parser.parse_args()

    if not firebase_enabled():
        print(
            "Firebase is not configured.\n"
            "1. Create a Firebase project and enable Cloud Firestore.\n"
            "2. Create a service account and download the JSON key locally "
            "(do not commit it).\n"
            "3. Set in .env:\n"
            "   FIREBASE_PROJECT_ID=...\n"
            "   FIREBASE_CREDENTIALS_PATH=/absolute/path/to/serviceAccount.json\n"
            "   # or FIREBASE_CREDENTIALS_JSON='{...}' for hosted API secrets\n"
            "   FIREBASE_ENABLED=true",
            file=sys.stderr,
        )
        return 1

    n_students = seed_students()
    print(f"Seeded {n_students} students into collection 'students'.")
    for student in DUMMY_STUDENTS:
        print(f"  - {student['full_name']} / {student['ucm_id']}")

    if args.with_login_logs:
        n_logs = seed_sample_login_logs(count=args.login_log_count)
        print(f"Wrote {n_logs} sample documents into collection 'login_logs'.")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
