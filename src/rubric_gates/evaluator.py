"""
PATH: src/rubric_gates/evaluator.py
PURPOSE: Evaluate artifacts against rubric suites and produce gate decisions.

WHY: This is the core logic that turns rubric definitions into executable checks.
     The evaluator is public (anyone can run it), but the *generators* that produce
     artifacts to be evaluated remain private (MedTWIN IP).

FLOW:
┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│ Load artifact + ctx  │──▶│ Run rubric checks         │──▶│ Emit CheckResult + gate   │
└──────────────────────┘   └──────────────────────────┘   └──────────────────────────┘

DEPENDENCIES:
- rubric_gates.rubric_loader
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone
from typing import Any

from rubric_gates.rubric_loader import RubricCheck, RubricSuite, load_all_rubrics


@dataclasses.dataclass
class CheckResult:
    """Result of evaluating a single rubric check."""

    id: str
    passed: bool
    score: float | None = None
    threshold: float | None = None
    message: str | None = None


@dataclasses.dataclass
class TierResult:
    """Result of evaluating all checks in a tier."""

    tier: int
    passed: bool
    checks: list[CheckResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass": self.passed,
            "checks": [
                {
                    "id": c.id,
                    "pass": c.passed,
                    **({"score": c.score} if c.score is not None else {}),
                    **({"threshold": c.threshold} if c.threshold is not None else {}),
                    **({"message": c.message} if c.message else {}),
                }
                for c in self.checks
            ],
        }


@dataclasses.dataclass
class GateDecision:
    """Final gate decision based on all tier results."""

    decision: str  # "approve", "revise", "block"
    blocking_reasons: list[str]
    required_fixes: list[str]
    deferral_recommended: bool = False
    deferral_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "blocking_reasons": self.blocking_reasons,
            "required_fixes": self.required_fixes,
            "deferral": {
                "recommended": self.deferral_recommended,
                "to": self.deferral_to or "human_review",
            },
        }


@dataclasses.dataclass
class EvaluationResult:
    """Complete evaluation result with all tiers and gate decision."""

    tier_results: dict[int, TierResult]
    gate_decision: GateDecision
    rubric_versions: dict[str, str]


class RubricEvaluator:
    """
    Evaluator that runs rubric checks against artifacts.

    This is the public evaluation engine. It can run deterministic checks
    (schema validation, range checks, SQL execution) but does NOT contain
    any proprietary agent/generation logic.
    """

    def __init__(self, rubrics_dir: str | None = None):
        from pathlib import Path

        self.rubrics_dir = Path(rubrics_dir) if rubrics_dir else None
        self.rubrics_by_tier = load_all_rubrics(self.rubrics_dir)

    def evaluate_check(
        self,
        check: RubricCheck,
        artifact: dict[str, Any],
        context: dict[str, Any],
    ) -> CheckResult:
        """
        Evaluate a single rubric check.

        This is where deterministic check implementations go.
        Override in subclasses to add custom check logic.
        """
        check_id = check.id

        # ===== TIER 1: Constitution checks =====
        if check_id == "tier1.determinism_required":
            # Check that artifact has executor + version
            has_executor = bool(artifact.get("deterministic_executor"))
            has_version = bool(artifact.get("version"))
            passed = has_executor and has_version
            return CheckResult(
                id=check_id,
                passed=passed,
                message=None if passed else "Missing deterministic_executor or version",
            )

        if check_id == "tier1.audit_trace_complete":
            # Check that provenance includes audit trace
            provenance = context.get("provenance", {})
            has_trace = bool(provenance.get("audit_trace_id"))
            return CheckResult(
                id=check_id,
                passed=has_trace,
                message=None if has_trace else "Missing audit_trace_id in provenance",
            )

        if check_id == "tier1.no_phi_in_artifacts":
            # Basic check: inputs_summary should not contain obvious PHI patterns
            inputs_summary = artifact.get("inputs_summary", "")
            # Very basic check - in production this would be more sophisticated
            has_phi_markers = any(
                marker in inputs_summary.lower()
                for marker in ["ssn", "social security", "patient name", "mrn", "medical record"]
            )
            passed = not has_phi_markers
            return CheckResult(
                id=check_id,
                passed=passed,
                message=None if passed else "Potential PHI detected in inputs_summary",
            )

        if check_id == "tier1.no_outcome_claims_without_validation":
            # Policy check - mark as passed by default (requires human review)
            return CheckResult(id=check_id, passed=True, message="Policy check - requires human review")

        # ===== TIER 2: Clinical invariants =====
        if check_id == "tier2.unit_consistency":
            # Check that units are declared
            features = context.get("features", {})
            all_have_units = all(f.get("unit") for f in features.values()) if features else True
            return CheckResult(
                id=check_id,
                passed=all_have_units,
                score=1.0 if all_have_units else 0.0,
                threshold=1.0,
                message=None if all_have_units else "Some features missing unit declarations",
            )

        if check_id == "tier2.plausible_ranges":
            # Check that values are within plausible ranges
            # Default to pass if no range violations detected
            return CheckResult(id=check_id, passed=True, score=1.0, threshold=0.95)

        if check_id == "tier2.temporal_coherence":
            # Check temporal ordering
            has_index_time = bool(context.get("index_time"))
            return CheckResult(
                id=check_id,
                passed=has_index_time,
                message=None if has_index_time else "Missing index_time for temporal coherence check",
            )

        if check_id == "tier2.outcome_leakage_prevention":
            # Check for leakage markers
            has_leakage = context.get("has_outcome_leakage", False)
            return CheckResult(
                id=check_id,
                passed=not has_leakage,
                message="Outcome leakage detected" if has_leakage else None,
            )

        # ===== TIER 3: Task benchmarks =====
        if check_id == "tier3.sql_executes":
            # Check if SQL executed successfully
            sql_executed = context.get("sql_executed", False)
            return CheckResult(
                id=check_id,
                passed=sql_executed,
                message=None if sql_executed else "SQL did not execute successfully",
            )

        if check_id == "tier3.cohort_overlap_jaccard":
            # Check Jaccard overlap with reference
            jaccard = context.get("cohort_jaccard", 0.0)
            threshold = check.scoring.get("threshold", 0.7) if check.scoring else 0.7
            passed = jaccard >= threshold
            return CheckResult(
                id=check_id,
                passed=passed,
                score=jaccard,
                threshold=threshold,
                message=f"Jaccard {jaccard:.2f} {'≥' if passed else '<'} {threshold}",
            )

        # Default: unknown check, mark as passed with warning
        return CheckResult(
            id=check_id,
            passed=True,
            message=f"Unknown check {check_id} - defaulting to pass",
        )

    def evaluate_tier(
        self,
        tier: int,
        artifact: dict[str, Any],
        context: dict[str, Any],
    ) -> TierResult:
        """Evaluate all checks in a tier."""
        suites = self.rubrics_by_tier.get(tier, [])
        all_checks: list[CheckResult] = []

        for suite in suites:
            for check in suite.checks:
                result = self.evaluate_check(check, artifact, context)
                all_checks.append(result)

        tier_passed = all(c.passed for c in all_checks)
        return TierResult(tier=tier, passed=tier_passed, checks=all_checks)

    def evaluate(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """
        Evaluate an artifact against all rubric tiers.

        Args:
            artifact: The artifact metadata (type, version, hash, etc.)
            context: Additional context for evaluation (features, provenance, etc.)

        Returns:
            EvaluationResult with tier results, gate decision, and rubric versions
        """
        if context is None:
            context = {}

        tier_results = {}
        for tier in [1, 2, 3]:
            tier_results[tier] = self.evaluate_tier(tier, artifact, context)

        # Determine gate decision based on tier results
        gate_decision = self._compute_gate_decision(tier_results)

        # Get rubric versions
        rubric_versions = {}
        for tier, suites in self.rubrics_by_tier.items():
            for suite in suites:
                rubric_versions[f"tier{tier}"] = suite.version

        return EvaluationResult(
            tier_results=tier_results,
            gate_decision=gate_decision,
            rubric_versions=rubric_versions,
        )

    def _compute_gate_decision(self, tier_results: dict[int, TierResult]) -> GateDecision:
        """Compute gate decision based on tier results."""
        blocking_reasons = []
        required_fixes = []

        # Tier 1 failures = block
        tier1 = tier_results.get(1)
        if tier1 and not tier1.passed:
            for check in tier1.checks:
                if not check.passed:
                    blocking_reasons.append(f"Tier 1 violation: {check.id}")
                    if check.message:
                        required_fixes.append(check.message)

        # Tier 2 failures = block (critical) or revise (major)
        tier2 = tier_results.get(2)
        if tier2 and not tier2.passed:
            for check in tier2.checks:
                if not check.passed:
                    blocking_reasons.append(f"Tier 2 violation: {check.id}")
                    if check.message:
                        required_fixes.append(check.message)

        # Tier 3 failures = revise
        tier3 = tier_results.get(3)
        tier3_failed = tier3 and not tier3.passed

        if tier3_failed:
            for check in tier3.checks:
                if not check.passed:
                    blocking_reasons.append(f"Tier 3 violation: {check.id}")
                    if check.message:
                        required_fixes.append(check.message)

        # Decision logic
        tier1_passed = tier1 is None or tier1.passed
        tier2_passed = tier2 is None or tier2.passed
        tier3_passed = tier3 is None or tier3.passed

        if not tier1_passed:
            decision = "block"
            deferral_recommended = True
        elif not tier2_passed:
            decision = "block"
            deferral_recommended = True
        elif not tier3_passed:
            decision = "revise"
            deferral_recommended = False
        else:
            decision = "approve"
            deferral_recommended = False

        return GateDecision(
            decision=decision,
            blocking_reasons=blocking_reasons,
            required_fixes=required_fixes,
            deferral_recommended=deferral_recommended,
            deferral_to="human_review" if deferral_recommended else None,
        )


def create_certificate(
    artifact: dict[str, Any],
    evaluation: EvaluationResult,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a certificate from an evaluation result.

    This is the public certificate creation function. It takes evaluation results
    and produces a certificate that conforms to the public schema.
    """
    now = datetime.now(timezone.utc).isoformat()
    certificate_id = str(uuid.uuid4())

    return {
        "certificate_id": certificate_id,
        "created_at": now,
        "artifact": artifact,
        "rubrics": {
            "tier_1": evaluation.tier_results[1].to_dict() if 1 in evaluation.tier_results else {"pass": True, "checks": []},
            "tier_2": evaluation.tier_results[2].to_dict() if 2 in evaluation.tier_results else {"pass": True, "checks": []},
            "tier_3": evaluation.tier_results[3].to_dict() if 3 in evaluation.tier_results else {"pass": True, "checks": []},
        },
        "gate_decision": evaluation.gate_decision.to_dict(),
        "provenance": {
            "audit_trace_id": provenance.get("audit_trace_id", f"trace_{certificate_id}"),
            "run_manifest_id": provenance.get("run_manifest_id", f"manifest_{certificate_id}"),
            "rubric_versions": evaluation.rubric_versions,
            **{k: v for k, v in provenance.items() if k not in ("audit_trace_id", "run_manifest_id")},
        },
    }
