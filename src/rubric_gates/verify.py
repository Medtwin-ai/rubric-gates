"""
PATH: src/rubric_gates/verify.py
PURPOSE: Certificate verifier implementation (schema validation + optional artifact hash checking).

WHY: Rubric Gates treats trust as a verifiable artifact. This module enables anyone
     (reviewers, partners, CI pipelines) to verify that a certificate conforms to the
     public contract, independent of MedTWIN’s internal agent systems.

FLOW:
┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│ Load JSON + schema   │──▶│ Validate schema          │──▶│ (Optional) hash verify    │
└──────────────────────┘   └──────────────────────────┘   └──────────────────────────┘

DEPENDENCIES:
- jsonschema
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

# Use a compatible validator - try newer version first, fall back to older
try:
    from jsonschema import Draft202012Validator as Validator
except ImportError:
    try:
        from jsonschema import Draft7Validator as Validator
    except ImportError:
        from jsonschema import Draft4Validator as Validator


@dataclasses.dataclass(frozen=True)
class VerifyResult:
    is_valid: bool
    errors: list[str]


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256_file(path: str) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _load_certificate_schema() -> dict[str, Any]:
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "certificate.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def verify_certificate(certificate: dict[str, Any], artifact_path: str | None = None) -> VerifyResult:
    errors: list[str] = []

    schema = _load_certificate_schema()
    validator = Validator(schema)

    schema_errors = sorted(validator.iter_errors(certificate), key=lambda e: list(e.absolute_path))
    for error in schema_errors:
        location = ".".join(str(p) for p in error.absolute_path) or "<root>"
        errors.append(f"{location}: {error.message}")

    if errors:
        return VerifyResult(is_valid=False, errors=errors)

    if artifact_path is not None:
        expected_hash = certificate.get("artifact", {}).get("hash")
        if not isinstance(expected_hash, str) or not expected_hash:
            return VerifyResult(
                is_valid=False,
                errors=["artifact.hash missing from certificate (required for --artifact verification)"],
            )

        actual_hash = _sha256_file(artifact_path)
        if actual_hash != expected_hash:
            return VerifyResult(
                is_valid=False,
                errors=[
                    "artifact hash mismatch",
                    f"expected: {expected_hash}",
                    f"actual:   {actual_hash}",
                ],
            )

    return VerifyResult(is_valid=True, errors=[])


def verify_certificate_file(certificate_path: str, artifact_path: str | None = None) -> VerifyResult:
    certificate = _read_json(certificate_path)
    if not isinstance(certificate, dict):
        return VerifyResult(is_valid=False, errors=["certificate JSON must be an object"])
    return verify_certificate(certificate=certificate, artifact_path=artifact_path)

