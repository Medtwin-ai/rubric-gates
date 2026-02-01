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


def cmd_datasets(args: argparse.Namespace) -> int:
    """List available datasets."""
    from rubric_gates.datasets.registry import DATASET_REGISTRY

    print("Rubric Gates - Available Datasets\n")
    print("=" * 70)

    for info in DATASET_REGISTRY.values():
        cred = "🔒 Credentialed" if info.credentialed else "🌐 Public"
        size = f"{info.expected_size_gb:.1f} GB" if info.expected_size_gb else "Unknown size"
        print(f"\n📊 {info.name} ({info.id})")
        print(f"   Version: {info.version}")
        print(f"   Access:  {cred}")
        print(f"   Size:    {size}")
        print(f"   Source:  {info.source}")

    print("\n" + "=" * 70)
    print(f"Total datasets: {len(DATASET_REGISTRY)}")
    print("\nTo download: rubric-gates download <dataset_id>")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    """Download a dataset from PhysioNet."""
    from rubric_gates.datasets import download_dataset, get_dataset_info

    dataset_id = args.dataset_id
    info = get_dataset_info(dataset_id)

    if info is None:
        print(f"❌ Unknown dataset: {dataset_id}")
        print("Run 'rubric-gates datasets' to see available datasets.")
        return 1

    print(f"📥 Downloading {info.name} v{info.version}...")

    if info.credentialed:
        import os
        if not os.environ.get("PHYSIONET_USER"):
            print("\n⚠️  This dataset requires PhysioNet credentials.")
            print("Set environment variables:")
            print("  export PHYSIONET_USER=your_username")
            print("  export PHYSIONET_PASS=your_password")
            return 1

    try:
        path = download_dataset(
            dataset_id,
            data_dir=args.data_dir,
            force=args.force,
        )
        print(f"✅ Downloaded to: {path}")
        return 0
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return 1


def cmd_manifest(args: argparse.Namespace) -> int:
    """Create or verify a dataset manifest."""
    from pathlib import Path
    from rubric_gates.datasets import create_manifest, load_manifest, verify_manifest

    if args.action == "create":
        print(f"📋 Creating manifest for {args.dataset_dir}...")
        manifest = create_manifest(
            dataset_dir=Path(args.dataset_dir),
            dataset_id=args.dataset_id,
            version=args.version,
        )
        output_path = Path(args.output or f"{args.dataset_id}_manifest.json")
        manifest.save(output_path)
        print(f"✅ Manifest saved to: {output_path}")
        print(f"   Files: {manifest.total_files}")
        print(f"   Size:  {manifest.total_size_bytes / 1e9:.2f} GB")
        print(f"   Root hash: {manifest.root_hash[:16]}...")
        return 0

    elif args.action == "verify":
        print(f"🔍 Verifying manifest against {args.dataset_dir}...")
        manifest = load_manifest(Path(args.manifest_file))
        is_valid, errors = verify_manifest(manifest, Path(args.dataset_dir))

        if is_valid:
            print("✅ Manifest verification passed")
            return 0
        else:
            print("❌ Manifest verification failed:")
            for error in errors:
                print(f"  - {error}")
            return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rubric-gates",
        description="Rubric Gates CLI: verify certificates, evaluate artifacts, manage datasets.",
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

    # datasets command
    subparsers.add_parser("datasets", help="List available datasets")

    # download command
    download_parser = subparsers.add_parser("download", help="Download a dataset from PhysioNet")
    download_parser.add_argument("dataset_id", help="Dataset identifier (e.g., mimic_iv)")
    download_parser.add_argument("--data-dir", default="./datasets", help="Directory to store datasets")
    download_parser.add_argument("--force", action="store_true", help="Re-download even if exists")

    # manifest command
    manifest_parser = subparsers.add_parser("manifest", help="Create or verify dataset manifests")
    manifest_subparsers = manifest_parser.add_subparsers(dest="action")

    create_parser = manifest_subparsers.add_parser("create", help="Create a manifest")
    create_parser.add_argument("dataset_dir", help="Path to dataset directory")
    create_parser.add_argument("--dataset-id", required=True, help="Dataset identifier")
    create_parser.add_argument("--version", required=True, help="Dataset version")
    create_parser.add_argument("-o", "--output", help="Output manifest file path")

    verify_manifest_parser = manifest_subparsers.add_parser("verify", help="Verify a manifest")
    verify_manifest_parser.add_argument("manifest_file", help="Path to manifest JSON")
    verify_manifest_parser.add_argument("dataset_dir", help="Path to dataset directory")

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
    elif args.command == "datasets":
        return cmd_datasets(args)
    elif args.command == "download":
        return cmd_download(args)
    elif args.command == "manifest":
        return cmd_manifest(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
