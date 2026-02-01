"""
PATH: src/rubric_gates/cli.py
PURPOSE: CLI entrypoint for Rubric Gates (verify + evaluate + info).

WHY: Third parties should be able to verify certificates and run evaluations
     without any proprietary agent code. This CLI is the "trust terminal".

FLOW:
┌─────────────────────┐   ┌──────────────────────────┐   ┌────────────────────┐
│ Load certificate    │──▶│ Validate against schema  │──▶│ Print pass/fail     │
└─────────────────────┘   └──────────────────────────┘   └────────────────────┘

DEPENDENCIES:
- rubric_gates.verify
- rubric_gates.evaluator
- rubric_gates.rubric_loader
"""

from __future__ import annotations

import argparse
import json
import sys

from rubric_gates.evaluator import RubricEvaluator, create_certificate
from rubric_gates.rubric_loader import get_rubric_versions, load_all_rubrics
from rubric_gates.verify import verify_certificate_file


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify a certificate."""
    result = verify_certificate_file(
        certificate_path=args.certificate_path,
        artifact_path=args.artifact_path,
    )

    if result.is_valid:
        print("✅ Certificate is valid")
        return 0

    print("❌ Certificate is invalid")
    for error in result.errors:
        print(f"  - {error}")
    return 1


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Evaluate an artifact and emit a certificate."""
    # Load artifact metadata from JSON
    with open(args.artifact_json, "r", encoding="utf-8") as f:
        artifact = json.load(f)

    # Load context if provided
    context = {}
    if args.context_json:
        with open(args.context_json, "r", encoding="utf-8") as f:
            context = json.load(f)

    # Run evaluation
    evaluator = RubricEvaluator(rubrics_dir=args.rubrics_dir)
    evaluation = evaluator.evaluate(artifact, context)

    # Create certificate
    provenance = context.get("provenance", {})
    certificate = create_certificate(artifact, evaluation, provenance)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(certificate, f, indent=2)
        print(f"✅ Certificate written to {args.output}")
    else:
        print(json.dumps(certificate, indent=2))

    # Return code based on decision
    decision = certificate["gate_decision"]["decision"]
    if decision == "approve":
        print(f"\n🟢 Gate decision: {decision}")
        return 0
    elif decision == "revise":
        print(f"\n🟡 Gate decision: {decision}")
        return 1
    else:
        print(f"\n🔴 Gate decision: {decision}")
        return 2


def cmd_info(args: argparse.Namespace) -> int:
    """Show rubric information."""
    rubrics = load_all_rubrics()
    versions = get_rubric_versions()

    print("Rubric Gates - Loaded Rubrics\n")
    print("=" * 50)

    for tier in [1, 2, 3]:
        suites = rubrics.get(tier, [])
        print(f"\nTier {tier}:")
        if not suites:
            print("  (no rubrics loaded)")
            continue

        for suite in suites:
            print(f"  📋 {suite.id} v{suite.version}")
            print(f"     {suite.purpose}")
            print(f"     Checks ({len(suite.checks)}):")
            for check in suite.checks:
                print(f"       - {check.id} [{check.severity}] → {check.gate}")

    print("\n" + "=" * 50)
    print(f"Total rubric suites: {sum(len(s) for s in rubrics.values())}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rubric-gates",
        description="Rubric Gates CLI: verify certificates, evaluate artifacts, and inspect rubrics.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify a certificate")
    verify_parser.add_argument("certificate_path", help="Path to certificate JSON file")
    verify_parser.add_argument(
        "--artifact",
        dest="artifact_path",
        default=None,
        help="Optional path to artifact file (hash will be checked)",
    )

    # evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate an artifact and emit certificate")
    eval_parser.add_argument("artifact_json", help="Path to artifact metadata JSON")
    eval_parser.add_argument("--context", dest="context_json", help="Path to context JSON (optional)")
    eval_parser.add_argument("--rubrics-dir", dest="rubrics_dir", help="Custom rubrics directory")
    eval_parser.add_argument("-o", "--output", help="Output certificate to file")

    # info command
    subparsers.add_parser("info", help="Show loaded rubrics information")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "verify":
        return cmd_verify(args)
    elif args.command == "evaluate":
        return cmd_evaluate(args)
    elif args.command == "info":
        return cmd_info(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
