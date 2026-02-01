"""
PATH: src/rubric_gates/__init__.py
PURPOSE: Public Rubric Gates package entrypoint.

WHY: Keep the verifier + schema utilities in a small, importable library that can be
     used by the public harness and by the private service (without exposing agents).

DEPENDENCIES:
- jsonschema
- PyYAML
"""

from rubric_gates.evaluator import (
    CheckResult,
    EvaluationResult,
    GateDecision,
    RubricEvaluator,
    TierResult,
    create_certificate,
)
from rubric_gates.rubric_loader import (
    RubricCheck,
    RubricSuite,
    get_rubric_versions,
    load_all_rubrics,
    load_rubric_file,
)
from rubric_gates.verify import VerifyResult, verify_certificate, verify_certificate_file

__all__ = [
    "__version__",
    # Evaluator
    "CheckResult",
    "EvaluationResult",
    "GateDecision",
    "RubricEvaluator",
    "TierResult",
    "create_certificate",
    # Rubric loader
    "RubricCheck",
    "RubricSuite",
    "get_rubric_versions",
    "load_all_rubrics",
    "load_rubric_file",
    # Verifier
    "VerifyResult",
    "verify_certificate",
    "verify_certificate_file",
]

__version__ = "0.1.0"

