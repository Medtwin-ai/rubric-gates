"""
PATH: src/rubric_gates/adapters/__init__.py
PURPOSE: Dataset adapters that transform raw data into canonical format.

WHY: Different datasets have different schemas. Adapters provide:
     - Standardized patient/admission/event views
     - Consistent naming conventions
     - Unit normalization
     - Temporal alignment

ADAPTER CONTRACT:
    Every adapter must implement:
    - load_patients() -> DataFrame with patient demographics
    - load_admissions() -> DataFrame with admission events
    - load_events(event_type) -> DataFrame with clinical events
    - get_cohort_sql(criteria) -> SQL query for cohort selection
"""

from rubric_gates.adapters.base import (
    BaseAdapter,
    AdapterConfig,
    CohortCriteria,
    PatientRecord,
    AdmissionRecord,
    ClinicalEvent,
)

__all__ = [
    "BaseAdapter",
    "AdapterConfig",
    "CohortCriteria",
    "PatientRecord",
    "AdmissionRecord",
    "ClinicalEvent",
]
