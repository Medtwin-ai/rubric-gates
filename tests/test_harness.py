"""
PATH: tests/test_harness.py
PURPOSE: Tests for the benchmark harness.
"""

import tempfile
from pathlib import Path

import pytest

from rubric_gates.harness import (
    BenchmarkHarness,
    DatasetSpec,
    RunConfig,
    create_run_config,
    generate_run_manifest,
)


def sample_artifact_generator(dataset_spec):
    """Generate sample artifacts for testing."""
    artifacts = []

    # Artifact 1: Should pass
    artifact1 = {
        "type": "cohort_spec",
        "version": "1.0.0",
        "hash": "abc123",
        "deterministic_executor": "duckdb+sql",
    }
    context1 = {
        "provenance": {"audit_trace_id": "trace_001"},
        "index_time": "2024-01-01T00:00:00Z",
        "sql_executed": True,
        "cohort_jaccard": 0.85,
    }
    artifacts.append((artifact1, context1))

    # Artifact 2: Should fail (low Jaccard)
    artifact2 = {
        "type": "cohort_spec",
        "version": "1.0.0",
        "hash": "def456",
        "deterministic_executor": "duckdb+sql",
    }
    context2 = {
        "provenance": {"audit_trace_id": "trace_002"},
        "index_time": "2024-01-01T00:00:00Z",
        "sql_executed": True,
        "cohort_jaccard": 0.5,  # Below threshold
    }
    artifacts.append((artifact2, context2))

    return artifacts


class TestBenchmarkHarness:
    """Tests for BenchmarkHarness."""

    def test_run_benchmark(self):
        """Test running a benchmark with sample data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                run_id="test_run",
                datasets=[
                    DatasetSpec(
                        id="test_dataset",
                        name="Test Dataset",
                        source="local/test",
                        version="1.0.0",
                    )
                ],
                output_dir=tmpdir,
                seed=42,
            )

            harness = BenchmarkHarness(config)
            result = harness.run(sample_artifact_generator)

            assert result.run_id == "test_run"
            assert len(result.dataset_results) == 1
            assert result.dataset_results[0].artifact_count == 2
            assert result.dataset_results[0].pass_count == 1
            assert result.dataset_results[0].revise_count == 1
            assert result.summary["pass_rate"] == 0.5

            # Check that files were created
            output_path = Path(tmpdir) / "test_run"
            assert output_path.exists()
            assert (output_path / "summary.json").exists()
            assert (output_path / "test_dataset").exists()


class TestRunConfig:
    """Tests for run configuration."""

    def test_create_run_config(self):
        """Test creating a run config from dataset specs."""
        datasets = [
            {
                "id": "mimic_iv",
                "name": "MIMIC-IV",
                "source": "physionet/mimiciv",
                "version": "2.2",
            },
            {
                "id": "eicu",
                "name": "eICU-CRD",
                "source": "physionet/eicu",
                "version": "2.0",
            },
        ]

        config = create_run_config(datasets, output_dir="./test_runs")

        assert len(config.datasets) == 2
        assert config.datasets[0].id == "mimic_iv"
        assert config.output_dir == "./test_runs"
        assert config.seed == 42

    def test_generate_run_manifest(self):
        """Test generating a run manifest."""
        config = RunConfig(
            run_id="test_run",
            datasets=[
                DatasetSpec(
                    id="test",
                    name="Test",
                    source="local/test",
                    version="1.0.0",
                    hash="sha256:abc123",
                )
            ],
            seed=42,
        )

        manifest = generate_run_manifest(config)

        assert manifest["run_id"] == "test_run"
        assert len(manifest["datasets"]) == 1
        assert manifest["datasets"][0]["hash"] == "sha256:abc123"
        assert "rubric_versions" in manifest
        assert manifest["config"]["seed"] == 42
