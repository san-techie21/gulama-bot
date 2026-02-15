#!/usr/bin/env python3
"""
Gulama security self-audit script.

Runs the SecurityDoctor and prints a formatted report.
Can be used standalone or as part of CI/CD pipelines.

Usage:
    python scripts/security_audit.py
    python scripts/security_audit.py --json
    python scripts/security_audit.py --strict  # exit 1 on any failure
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cli.doctor import SecurityDoctor


def main() -> int:
    parser = argparse.ArgumentParser(description="Gulama security self-audit")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with code 1 if any check fails",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config.toml for configuration checks",
    )
    args = parser.parse_args()

    config: dict = {}
    if args.config:
        try:
            import tomli
            with open(args.config, "rb") as f:
                config = tomli.load(f)
        except Exception as e:
            print(f"Warning: Could not load config: {e}", file=sys.stderr)

    doctor = SecurityDoctor(config=config)
    results = doctor.run_all_checks()

    if args.json:
        output = {
            "summary": doctor.get_summary(),
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "message": r.message,
                    "details": r.details,
                }
                for r in results
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(doctor.format_report())

    summary = doctor.get_summary()
    if args.strict and summary["failed"] > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
