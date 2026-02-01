"""
PATH: tests/test_evaluator.py
PURPOSE: Tests for the rubric evaluator.
"""

import pytest

from rubric_gates.evaluator import RubricEvaluator, create_certificate


class TestRubricEvaluator:
    """Tests for RubricEvaluator."""

    def test_evaluate_passing_artifact(self):
        """Test evaluation of a well-formed artifact."""
        evaluator = RubricEvaluator()

        artifact = {
            "type": "cohort_spec",
            "version": "1.0.0",
            "hash": "abc123",
            "deterministic_executor": "duckdb+sql",
            "inputs_summary": "De-identified clinical data",
        }

        context = {
            "provenance": {
                "audit_trace_id": "trace_001",
                "run_manifest_id": "manifest_001",
            },
            "features": {
                "age": {"unit": "years"},
                "weight": {"unit": "kg"},
            },
            "index_time": "2024-01-01T00:00:00Z",
            "sql_executed": True,
            "cohort_jaccard": 0.85,
        }

        result = evaluator.evaluate(artifact, context)

        assert result.gate_decision.decision == "approve"
        assert result.tier_results[1].passed
        assert result.tier_results[2].passed
        assert result.tier_results[3].passed

    def test_evaluate_missing_executor(self):
        """Test that missing executor fails Tier 1."""
        evaluator = RubricEvaluator()

        artifact = {
            "type": "cohort_spec",
            "version": "1.0.0",
            "hash": "abc123",
            # Missing deterministic_executor
        }

        context = {
            "provenance": {"audit_trace_id": "trace_001"},
        }

        result = evaluator.evaluate(artifact, context)

        assert not result.tier_results[1].passed
        assert result.gate_decision.decision == "block"

    def test_evaluate_low_jaccard(self):
        """Test that low Jaccard score results in revise decision."""
        evaluator = RubricEvaluator()

        artifact = {
            "type": "cohort_spec",
            "version": "1.0.0",
            "hash": "abc123",
            "deterministic_executor": "duckdb+sql",
        }

        context = {
            "provenance": {"audit_trace_id": "trace_001"},
            "index_time": "2024-01-01T00:00:00Z",
            "sql_executed": True,
            "cohort_jaccard": 0.5,  # Below 0.7 threshold
        }

        result = evaluator.evaluate(artifact, context)

        # Tier 1 and 2 should pass
        assert result.tier_results[1].passed
        assert result.tier_results[2].passed
        # Tier 3 should fail
        assert not result.tier_results[3].passed
        # Decision should be revise (not block)
        assert result.gate_decision.decision == "revise"


class TestCreateCertificate:
    """Tests for certificate creation."""

    def test_create_certificate_structure(self):
        """Test that created certificate has correct structure."""
        evaluator = RubricEvaluator()

        artifact = {
            "type": "cohort_spec",
            "version": "1.0.0",
            "hash": "abc123",
            "deterministic_executor": "duckdb+sql",
        }

        context = {
            "provenance": {
                "audit_trace_id": "trace_001",
                "run_manifest_id": "manifest_001",
            },
            "index_time": "2024-01-01T00:00:00Z",
            "sql_executed": True,
            "cohort_jaccard": 0.9,
        }

        evaluation = evaluator.evaluate(artifact, context)
        certificate = create_certificate(artifact, evaluation, context.get("provenance", {}))

        # Check required fields
        assert "certificate_id" in certificate
        assert "created_at" in certificate
        assert "artifact" in certificate
        assert "rubrics" in certificate
        assert "gate_decision" in certificate
        assert "provenance" in certificate

        # Check rubric tiers
        assert "tier_1" in certificate["rubrics"]
        assert "tier_2" in certificate["rubrics"]
        assert "tier_3" in certificate["rubrics"]

        # Check gate decision
        assert certificate["gate_decision"]["decision"] in ("approve", "revise", "block")
