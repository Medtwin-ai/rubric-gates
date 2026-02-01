"""
PATH: src/rubric_gates/cli.py
PURPOSE: CLI entrypoint for verifying Rubric Gates certificates.

WHY: Third parties should be able to verify the certificate contract without any
     proprietary agent code. This CLI is the “trust terminal”.

FLOW:
┌─────────────────────┐   ┌──────────────────────────┐   ┌────────────────────┐
│ Load certificate    │──▶│ Validate against schema  │──▶│ Print pass/fail     │
└─────────────────────┘   └──────────────────────────┘   └────────────────────┘

DEPENDENCIES:
- rubric_gates.verify
"""

from __future__ import annotations

import argparse
import sys

from rubric_gates.verify import verify_certificate_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rubric-gates-verify",
        description="Verify a Rubric Gates certificate (schema + optional artifact hash check).",
    )

    parser.add_argument(
        "certificate_path",
        help="Path to certificate JSON file.",
    )

    parser.add_argument(
        "--artifact",
        dest="artifact_path",
        default=None,
        help="Optional path to the artifact referenced by the certificate (hash will be checked).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    result = verify_certificate_file(
        certificate_path=args.certificate_path,
        artifact_path=args.artifact_path,
    )

    if result.is_valid:
        print("✅ Certificate is valid")
        return 0

    print("❌ Certificate is invalid")
    for error in result.errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

