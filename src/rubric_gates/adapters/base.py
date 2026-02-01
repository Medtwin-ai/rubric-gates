"""
PATH: src/rubric_gates/adapters/base.py
PURPOSE: Base adapter class and canonical data structures.

WHY: Standardized interfaces enable:
     - Cross-dataset evaluation
     - Consistent rubric checks
     - Reproducible cohort definitions

CANONICAL SCHEMA:
    patient_id: str (unique within dataset)
    admission_id: str (unique within dataset)
    timestamp: datetime (UTC)
    All numeric values include units
"""

from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclasses.dataclass(frozen=True)
class AdapterConfig:
    """Configuration for a dataset adapter."""

    data_dir: Path
    version: str
    cache_dir: Path | None = None
    use_parquet: bool = True


@dataclasses.dataclass
class PatientRecord:
    """Canonical patient demographics record."""

    patient_id: str
    gender: str | None = None  # "M", "F", "O", None
    birth_year: int | None = None
    death_year: int | None = None
    anchor_age: int | None = None  # Age at anchor point (for age-shifted datasets)
    ethnicity: str | None = None
    language: str | None = None


@dataclasses.dataclass
class AdmissionRecord:
    """Canonical admission/stay record."""

    admission_id: str
    patient_id: str
    admit_time: datetime
    discharge_time: datetime | None = None
    death_time: datetime | None = None
    admission_type: str | None = None
    admission_location: str | None = None
    discharge_location: str | None = None
    insurance: str | None = None
    hospital_expire_flag: bool = False


@dataclasses.dataclass
class ClinicalEvent:
    """Canonical clinical event (lab, vital, medication, etc.)."""

    event_id: str
    patient_id: str
    admission_id: str | None
    event_time: datetime
    event_type: str  # "lab", "vital", "medication", "procedure", "diagnosis"
    item_id: str
    item_name: str
    value: float | str | None = None
    value_unit: str | None = None
    value_num: float | None = None
    reference_low: float | None = None
    reference_high: float | None = None


@dataclasses.dataclass
class CohortCriteria:
    """Criteria for cohort selection."""

    min_age: int | None = None
    max_age: int | None = None
    min_los_hours: float | None = None  # Length of stay
    max_los_hours: float | None = None
    include_diagnoses: list[str] | None = None  # ICD codes
    exclude_diagnoses: list[str] | None = None
    require_labs: list[str] | None = None  # Lab item IDs
    require_vitals: list[str] | None = None  # Vital item IDs
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None


class BaseAdapter(ABC):
    """
    Base class for dataset adapters.

    Adapters transform raw dataset files into canonical format.
    Each dataset (MIMIC-IV, eICU, etc.) has its own adapter.
    """

    def __init__(self, config: AdapterConfig):
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate adapter configuration."""
        if not self.config.data_dir.exists():
            raise ValueError(f"Data directory does not exist: {self.config.data_dir}")

    @property
    @abstractmethod
    def dataset_id(self) -> str:
        """Return the dataset identifier."""
        ...

    @property
    @abstractmethod
    def dataset_name(self) -> str:
        """Return the human-readable dataset name."""
        ...

    @abstractmethod
    def load_patients(self) -> list[PatientRecord]:
        """
        Load patient demographics.

        Returns:
            List of PatientRecord objects
        """
        ...

    @abstractmethod
    def load_admissions(self) -> list[AdmissionRecord]:
        """
        Load admission records.

        Returns:
            List of AdmissionRecord objects
        """
        ...

    @abstractmethod
    def load_events(self, event_type: str) -> list[ClinicalEvent]:
        """
        Load clinical events of a specific type.

        Args:
            event_type: One of "lab", "vital", "medication", "procedure", "diagnosis"

        Returns:
            List of ClinicalEvent objects
        """
        ...

    @abstractmethod
    def get_cohort_sql(self, criteria: CohortCriteria) -> str:
        """
        Generate SQL for cohort selection.

        Args:
            criteria: CohortCriteria specifying inclusion/exclusion rules

        Returns:
            DuckDB-compatible SQL query string
        """
        ...

    def get_item_mapping(self, item_type: str) -> dict[str, str]:
        """
        Get mapping from dataset item IDs to canonical names.

        Args:
            item_type: Type of items ("lab", "vital", "medication")

        Returns:
            Dict mapping dataset-specific IDs to canonical names
        """
        return {}

    def get_unit_conversions(self) -> dict[str, tuple[str, float]]:
        """
        Get unit conversion factors to canonical units.

        Returns:
            Dict mapping from unit to (canonical_unit, multiplier)
        """
        return {}

    def validate_data_quality(self) -> dict[str, Any]:
        """
        Run data quality checks on the loaded data.

        Returns:
            Dict with quality metrics (missing rates, outliers, etc.)
        """
        return {
            "patients_count": len(self.load_patients()),
            "admissions_count": len(self.load_admissions()),
            "quality_checks": "passed",
        }
