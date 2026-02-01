"""
PATH: src/rubric_gates/harness.py
PURPOSE: Benchmark harness for running reproducible rubric evaluations across datasets.

WHY: Research reproducibility requires:
     1. Versioned datasets (manifests)
     2. Versioned rubrics
     3. Deterministic execution
     4. Auditable results

FLOW:
┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│ Load run manifest    │──▶│ Execute per-dataset runs  │──▶│ Aggregate + report       │
└──────────────────────┘   └──────────────────────────┘   └──────────────────────────┘

DEPENDENCIES:
- rubric_gates.evaluator
- rubric_gates.rubric_loader
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from rubric_gates.evaluator import RubricEvaluator, create_certificate
from rubric_gates.rubric_loader import get_rubric_versions


@dataclasses.dataclass
class DatasetSpec:
    """Specification for a benchmark dataset."""

    id: str
    name: str
    source: str  # e.g., "physionet/mimiciv" or local path
    version: str
    hash: str | None = None  # SHA-256 of dataset bundle
    adapter: str | None = None  # Python module for loading


@dataclasses.dataclass
class RunConfig:
    """Configuration for a benchmark run."""

    run_id: str
    datasets: list[DatasetSpec]
    rubrics_dir: str | None = None
    output_dir: str = "./runs"
    seed: int = 42
    parallel: bool = False


@dataclasses.dataclass
class DatasetResult:
    """Result of evaluating one dataset."""

    dataset_id: str
    artifact_count: int
    pass_count: int
    revise_count: int
    block_count: int
    certificates: list[dict[str, Any]]
    duration_seconds: float


@dataclasses.dataclass
class BenchmarkResult:
    """Complete benchmark result across all datasets."""

    run_id: str
    started_at: str
    completed_at: str
    rubric_versions: dict[str, str]
    dataset_results: list[DatasetResult]
    summary: dict[str, Any]


class BenchmarkHarness:
    """
    Harness for running reproducible rubric benchmarks.

    The harness:
    1. Loads a run manifest (datasets + config)
    2. For each dataset, loads artifacts via adapters
    3. Evaluates each artifact against rubrics
    4. Collects metrics and certificates
    5. Outputs a reproducibility report
    """

    def __init__(self, config: RunConfig):
        self.config = config
        self.evaluator = RubricEvaluator(rubrics_dir=config.rubrics_dir)
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        artifact_generator: Callable[[DatasetSpec], list[tuple[dict, dict]]],
    ) -> BenchmarkResult:
        """
        Run the benchmark.

        Args:
            artifact_generator: Function that takes a DatasetSpec and returns
                                list of (artifact, context) tuples to evaluate.

        Returns:
            BenchmarkResult with all metrics and certificates.
        """
        started_at = datetime.now(timezone.utc).isoformat()
        dataset_results: list[DatasetResult] = []

        for dataset_spec in self.config.datasets:
            result = self._evaluate_dataset(dataset_spec, artifact_generator)
            dataset_results.append(result)

        completed_at = datetime.now(timezone.utc).isoformat()

        # Compute summary
        total_artifacts = sum(r.artifact_count for r in dataset_results)
        total_pass = sum(r.pass_count for r in dataset_results)
        total_revise = sum(r.revise_count for r in dataset_results)
        total_block = sum(r.block_count for r in dataset_results)

        summary = {
            "total_datasets": len(dataset_results),
            "total_artifacts": total_artifacts,
            "pass_rate": total_pass / total_artifacts if total_artifacts > 0 else 0,
            "revise_rate": total_revise / total_artifacts if total_artifacts > 0 else 0,
            "block_rate": total_block / total_artifacts if total_artifacts > 0 else 0,
            "total_duration_seconds": sum(r.duration_seconds for r in dataset_results),
        }

        result = BenchmarkResult(
            run_id=self.config.run_id,
            started_at=started_at,
            completed_at=completed_at,
            rubric_versions=get_rubric_versions(),
            dataset_results=dataset_results,
            summary=summary,
        )

        # Save result
        self._save_result(result)

        return result

    def _evaluate_dataset(
        self,
        dataset_spec: DatasetSpec,
        artifact_generator: Callable[[DatasetSpec], list[tuple[dict, dict]]],
    ) -> DatasetResult:
        """Evaluate all artifacts from a single dataset."""
        start_time = time.time()

        # Generate artifacts
        artifacts_and_contexts = artifact_generator(dataset_spec)

        certificates: list[dict[str, Any]] = []
        pass_count = 0
        revise_count = 0
        block_count = 0

        for artifact, context in artifacts_and_contexts:
            # Add provenance
            if "provenance" not in context:
                context["provenance"] = {}
            context["provenance"]["dataset_id"] = dataset_spec.id
            context["provenance"]["dataset_version"] = dataset_spec.version

            # Evaluate
            evaluation = self.evaluator.evaluate(artifact, context)

            # Create certificate
            certificate = create_certificate(artifact, evaluation, context.get("provenance", {}))
            certificates.append(certificate)

            # Count decisions
            decision = certificate["gate_decision"]["decision"]
            if decision == "approve":
                pass_count += 1
            elif decision == "revise":
                revise_count += 1
            else:
                block_count += 1

        duration = time.time() - start_time

        return DatasetResult(
            dataset_id=dataset_spec.id,
            artifact_count=len(certificates),
            pass_count=pass_count,
            revise_count=revise_count,
            block_count=block_count,
            certificates=certificates,
            duration_seconds=duration,
        )

    def _save_result(self, result: BenchmarkResult) -> None:
        """Save benchmark result to output directory."""
        run_dir = self.output_dir / result.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        summary_path = run_dir / "summary.json"
        summary_data = {
            "run_id": result.run_id,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "rubric_versions": result.rubric_versions,
            "summary": result.summary,
            "datasets": [
                {
                    "dataset_id": r.dataset_id,
                    "artifact_count": r.artifact_count,
                    "pass_count": r.pass_count,
                    "revise_count": r.revise_count,
                    "block_count": r.block_count,
                    "duration_seconds": r.duration_seconds,
                }
                for r in result.dataset_results
            ],
        }
        summary_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

        # Save certificates per dataset
        for ds_result in result.dataset_results:
            ds_dir = run_dir / ds_result.dataset_id
            ds_dir.mkdir(parents=True, exist_ok=True)

            for i, cert in enumerate(ds_result.certificates):
                cert_path = ds_dir / f"certificate_{i:04d}.json"
                cert_path.write_text(json.dumps(cert, indent=2), encoding="utf-8")


def create_run_config(
    datasets: list[dict[str, Any]],
    output_dir: str = "./runs",
    seed: int = 42,
) -> RunConfig:
    """
    Create a RunConfig from a list of dataset specifications.

    Args:
        datasets: List of dicts with keys: id, name, source, version, hash (optional)
        output_dir: Directory to save run outputs
        seed: Random seed for reproducibility

    Returns:
        RunConfig instance
    """
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    dataset_specs = [
        DatasetSpec(
            id=d["id"],
            name=d["name"],
            source=d["source"],
            version=d["version"],
            hash=d.get("hash"),
            adapter=d.get("adapter"),
        )
        for d in datasets
    ]

    return RunConfig(
        run_id=run_id,
        datasets=dataset_specs,
        output_dir=output_dir,
        seed=seed,
    )


def generate_run_manifest(config: RunConfig) -> dict[str, Any]:
    """
    Generate a run manifest JSON for reproducibility.

    The manifest captures:
    - Dataset versions and hashes
    - Rubric versions
    - Execution config (seed, etc.)
    """
    return {
        "$schema": "https://github.com/Medtwin-ai/rubric-gates/schemas/run_manifest.schema.json",
        "run_id": config.run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "datasets": [
            {
                "id": ds.id,
                "name": ds.name,
                "source": ds.source,
                "version": ds.version,
                "hash": ds.hash,
            }
            for ds in config.datasets
        ],
        "rubric_versions": get_rubric_versions(),
        "config": {
            "seed": config.seed,
            "rubrics_dir": config.rubrics_dir,
        },
    }
