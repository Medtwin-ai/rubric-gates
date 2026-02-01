"""
PATH: src/rubric_gates/rubric_loader.py
PURPOSE: Load and validate rubric definitions from YAML files.

WHY: Rubrics must be versioned, auditable, and executable. This loader provides
     a clean interface to load rubric suites from the public repo structure.

FLOW:
┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│ Discover YAML files  │──▶│ Parse + validate schema   │──▶│ Return RubricSuite objs   │
└──────────────────────┘   └──────────────────────────┘   └──────────────────────────┘

DEPENDENCIES:
- PyYAML
- jsonschema
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import yaml

# Use a compatible validator - try newer version first, fall back to older
try:
    from jsonschema import Draft202012Validator as Validator
except ImportError:
    try:
        from jsonschema import Draft7Validator as Validator
    except ImportError:
        from jsonschema import Draft4Validator as Validator


@dataclasses.dataclass(frozen=True)
class RubricCheck:
    """A single rubric check definition."""

    id: str
    description: str
    check_type: str
    severity: str
    gate: str
    required_fixes: list[str]
    scoring: dict[str, Any] | None = None


@dataclasses.dataclass(frozen=True)
class RubricSuite:
    """A complete rubric suite (Tier 1, 2, or 3)."""

    id: str
    tier: int
    version: str
    purpose: str
    checks: list[RubricCheck]

    def get_check(self, check_id: str) -> RubricCheck | None:
        for check in self.checks:
            if check.id == check_id:
                return check
        return None


def _get_rubric_schema() -> dict[str, Any]:
    """Load the rubric JSON schema."""
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "rubric.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _get_default_rubrics_dir() -> Path:
    """Get the default rubrics directory (relative to package)."""
    return Path(__file__).resolve().parents[2] / "rubrics"


def load_rubric_file(path: Path) -> RubricSuite:
    """Load a single rubric suite from a YAML file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    # Validate against schema
    schema = _get_rubric_schema()
    validator = Validator(schema)
    errors = list(validator.iter_errors(raw))
    if errors:
        error_msgs = [f"{'.'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors]
        raise ValueError(f"Invalid rubric file {path}: {error_msgs}")

    suite_data = raw["rubric_suite"]

    checks = []
    for check_data in suite_data.get("checks", []):
        checks.append(
            RubricCheck(
                id=check_data["id"],
                description=check_data["description"],
                check_type=check_data["check_type"],
                severity=check_data["severity"],
                gate=check_data["gate"],
                required_fixes=check_data.get("required_fixes", []),
                scoring=check_data.get("scoring"),
            )
        )

    return RubricSuite(
        id=suite_data["id"],
        tier=suite_data["tier"],
        version=suite_data["version"],
        purpose=suite_data.get("purpose", ""),
        checks=checks,
    )


def load_all_rubrics(rubrics_dir: Path | None = None) -> dict[int, list[RubricSuite]]:
    """
    Load all rubric suites organized by tier.

    Returns:
        dict mapping tier number (1, 2, 3) to list of RubricSuites
    """
    if rubrics_dir is None:
        rubrics_dir = _get_default_rubrics_dir()

    rubrics_by_tier: dict[int, list[RubricSuite]] = {1: [], 2: [], 3: []}

    for tier_dir in ["tier1", "tier2", "tier3"]:
        tier_path = rubrics_dir / tier_dir
        if not tier_path.exists():
            continue

        tier_num = int(tier_dir[-1])

        for yaml_file in tier_path.glob("*.yaml"):
            try:
                suite = load_rubric_file(yaml_file)
                rubrics_by_tier[tier_num].append(suite)
            except Exception as e:
                # Log but don't fail on individual file errors
                print(f"Warning: Failed to load {yaml_file}: {e}")

    return rubrics_by_tier


def get_rubric_versions(rubrics_dir: Path | None = None) -> dict[str, str]:
    """Get a mapping of rubric suite IDs to their versions."""
    all_rubrics = load_all_rubrics(rubrics_dir)
    versions = {}
    for tier_suites in all_rubrics.values():
        for suite in tier_suites:
            versions[suite.id] = suite.version
    return versions
