"""
PATH: src/rubric_gates/adapters/mimic_iv.py
PURPOSE: Adapter for MIMIC-IV dataset.

MIMIC-IV SCHEMA NOTES:
- patients.csv: Demographics (anchor_age, anchor_year, anchor_year_group, dod)
- admissions.csv: Hospital admissions
- icustays.csv: ICU stays (subset of admissions)
- chartevents.csv: Vital signs and other charted data
- labevents.csv: Laboratory measurements
- prescriptions.csv: Medications

TEMPORAL NOTES:
- MIMIC-IV uses de-identified dates shifted to future
- anchor_year + (real_year - anchor_year_group) = shifted_year
- All times are shifted consistently within a patient

DEPENDENCIES:
- pandas (for CSV loading)
- duckdb (for SQL execution)
"""

from __future__ import annotations

import gzip
from datetime import datetime
from pathlib import Path
from typing import Any

from rubric_gates.adapters.base import (
    AdapterConfig,
    AdmissionRecord,
    BaseAdapter,
    ClinicalEvent,
    CohortCriteria,
    PatientRecord,
)


class MIMICIVAdapter(BaseAdapter):
    """
    Adapter for MIMIC-IV v2.2 dataset.

    Expected directory structure:
        data_dir/
        ├── hosp/
        │   ├── patients.csv.gz
        │   ├── admissions.csv.gz
        │   ├── diagnoses_icd.csv.gz
        │   ├── labevents.csv.gz
        │   └── prescriptions.csv.gz
        └── icu/
            ├── icustays.csv.gz
            └── chartevents.csv.gz
    """

    @property
    def dataset_id(self) -> str:
        return "mimic_iv"

    @property
    def dataset_name(self) -> str:
        return "MIMIC-IV"

    def _read_csv(self, subdir: str, filename: str) -> list[dict[str, Any]]:
        """Read a CSV file (gzipped or plain) from the dataset."""
        base_path = self.config.data_dir / subdir

        # Try gzipped first
        gz_path = base_path / f"{filename}.csv.gz"
        if gz_path.exists():
            import csv
            import io

            with gzip.open(gz_path, "rt", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)

        # Try plain CSV
        csv_path = base_path / f"{filename}.csv"
        if csv_path.exists():
            import csv

            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)

        raise FileNotFoundError(f"Could not find {filename}.csv or {filename}.csv.gz in {base_path}")

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse MIMIC datetime string."""
        if not dt_str or dt_str.strip() == "":
            return None
        try:
            return datetime.fromisoformat(dt_str.replace(" ", "T"))
        except ValueError:
            return None

    def load_patients(self) -> list[PatientRecord]:
        """Load patient demographics from patients.csv."""
        rows = self._read_csv("hosp", "patients")

        patients = []
        for row in rows:
            patients.append(
                PatientRecord(
                    patient_id=row["subject_id"],
                    gender=row.get("gender"),
                    anchor_age=int(row["anchor_age"]) if row.get("anchor_age") else None,
                    death_year=int(row["dod"][:4]) if row.get("dod") else None,
                )
            )

        return patients

    def load_admissions(self) -> list[AdmissionRecord]:
        """Load admission records from admissions.csv."""
        rows = self._read_csv("hosp", "admissions")

        admissions = []
        for row in rows:
            admissions.append(
                AdmissionRecord(
                    admission_id=row["hadm_id"],
                    patient_id=row["subject_id"],
                    admit_time=self._parse_datetime(row.get("admittime")),
                    discharge_time=self._parse_datetime(row.get("dischtime")),
                    death_time=self._parse_datetime(row.get("deathtime")),
                    admission_type=row.get("admission_type"),
                    admission_location=row.get("admission_location"),
                    discharge_location=row.get("discharge_location"),
                    insurance=row.get("insurance"),
                    hospital_expire_flag=row.get("hospital_expire_flag") == "1",
                )
            )

        return admissions

    def load_events(self, event_type: str) -> list[ClinicalEvent]:
        """
        Load clinical events.

        Args:
            event_type: "lab", "vital", "medication", "diagnosis"
        """
        if event_type == "lab":
            return self._load_lab_events()
        elif event_type == "vital":
            return self._load_vital_events()
        elif event_type == "medication":
            return self._load_medication_events()
        elif event_type == "diagnosis":
            return self._load_diagnosis_events()
        else:
            raise ValueError(f"Unknown event type: {event_type}")

    def _load_lab_events(self) -> list[ClinicalEvent]:
        """Load laboratory events from labevents.csv."""
        rows = self._read_csv("hosp", "labevents")

        events = []
        for i, row in enumerate(rows):
            events.append(
                ClinicalEvent(
                    event_id=f"lab_{i}",
                    patient_id=row["subject_id"],
                    admission_id=row.get("hadm_id"),
                    event_time=self._parse_datetime(row.get("charttime")),
                    event_type="lab",
                    item_id=row["itemid"],
                    item_name=row.get("label", row["itemid"]),
                    value=row.get("value"),
                    value_unit=row.get("valueuom"),
                    value_num=float(row["valuenum"]) if row.get("valuenum") else None,
                    reference_low=float(row["ref_range_lower"]) if row.get("ref_range_lower") else None,
                    reference_high=float(row["ref_range_upper"]) if row.get("ref_range_upper") else None,
                )
            )

        return events

    def _load_vital_events(self) -> list[ClinicalEvent]:
        """Load vital sign events from chartevents.csv."""
        rows = self._read_csv("icu", "chartevents")

        # Vital sign item IDs in MIMIC-IV
        vital_items = {
            "220045": "Heart Rate",
            "220050": "Arterial Blood Pressure systolic",
            "220051": "Arterial Blood Pressure diastolic",
            "220052": "Arterial Blood Pressure mean",
            "220179": "Non Invasive Blood Pressure systolic",
            "220180": "Non Invasive Blood Pressure diastolic",
            "220181": "Non Invasive Blood Pressure mean",
            "220210": "Respiratory Rate",
            "223761": "Temperature Fahrenheit",
            "223762": "Temperature Celsius",
            "220277": "SpO2",
        }

        events = []
        for i, row in enumerate(rows):
            if row["itemid"] not in vital_items:
                continue

            events.append(
                ClinicalEvent(
                    event_id=f"vital_{i}",
                    patient_id=row["subject_id"],
                    admission_id=row.get("hadm_id"),
                    event_time=self._parse_datetime(row.get("charttime")),
                    event_type="vital",
                    item_id=row["itemid"],
                    item_name=vital_items.get(row["itemid"], row["itemid"]),
                    value=row.get("value"),
                    value_unit=row.get("valueuom"),
                    value_num=float(row["valuenum"]) if row.get("valuenum") else None,
                )
            )

        return events

    def _load_medication_events(self) -> list[ClinicalEvent]:
        """Load medication events from prescriptions.csv."""
        rows = self._read_csv("hosp", "prescriptions")

        events = []
        for i, row in enumerate(rows):
            events.append(
                ClinicalEvent(
                    event_id=f"med_{i}",
                    patient_id=row["subject_id"],
                    admission_id=row.get("hadm_id"),
                    event_time=self._parse_datetime(row.get("starttime")),
                    event_type="medication",
                    item_id=row.get("drug", ""),
                    item_name=row.get("drug", ""),
                    value=row.get("dose_val_rx"),
                    value_unit=row.get("dose_unit_rx"),
                )
            )

        return events

    def _load_diagnosis_events(self) -> list[ClinicalEvent]:
        """Load diagnosis events from diagnoses_icd.csv."""
        rows = self._read_csv("hosp", "diagnoses_icd")

        events = []
        for i, row in enumerate(rows):
            events.append(
                ClinicalEvent(
                    event_id=f"dx_{i}",
                    patient_id=row["subject_id"],
                    admission_id=row.get("hadm_id"),
                    event_time=None,  # Diagnoses don't have timestamps
                    event_type="diagnosis",
                    item_id=row["icd_code"],
                    item_name=row["icd_code"],
                    value=row.get("icd_version"),
                )
            )

        return events

    def get_cohort_sql(self, criteria: CohortCriteria) -> str:
        """
        Generate DuckDB SQL for cohort selection.

        This SQL is deterministic and can be executed against the
        parquet/CSV files to produce the same cohort.
        """
        where_clauses = []

        if criteria.min_age is not None:
            where_clauses.append(f"p.anchor_age >= {criteria.min_age}")
        if criteria.max_age is not None:
            where_clauses.append(f"p.anchor_age <= {criteria.max_age}")

        if criteria.min_los_hours is not None:
            where_clauses.append(
                f"EXTRACT(EPOCH FROM (a.dischtime - a.admittime)) / 3600 >= {criteria.min_los_hours}"
            )
        if criteria.max_los_hours is not None:
            where_clauses.append(
                f"EXTRACT(EPOCH FROM (a.dischtime - a.admittime)) / 3600 <= {criteria.max_los_hours}"
            )

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"""
-- MIMIC-IV Cohort Selection
-- Generated by rubric-gates MIMICIVAdapter
-- Criteria: {criteria}

SELECT DISTINCT
    p.subject_id AS patient_id,
    a.hadm_id AS admission_id,
    p.gender,
    p.anchor_age,
    a.admittime,
    a.dischtime,
    a.hospital_expire_flag,
    EXTRACT(EPOCH FROM (a.dischtime - a.admittime)) / 3600 AS los_hours
FROM patients p
JOIN admissions a ON p.subject_id = a.subject_id
WHERE {where_clause}
ORDER BY p.subject_id, a.admittime
"""
        return sql.strip()

    def get_item_mapping(self, item_type: str) -> dict[str, str]:
        """Get MIMIC-IV item ID to canonical name mapping."""
        if item_type == "vital":
            return {
                "220045": "heart_rate",
                "220050": "sbp_arterial",
                "220051": "dbp_arterial",
                "220052": "map_arterial",
                "220179": "sbp_nibp",
                "220180": "dbp_nibp",
                "220181": "map_nibp",
                "220210": "respiratory_rate",
                "223761": "temperature_f",
                "223762": "temperature_c",
                "220277": "spo2",
            }
        elif item_type == "lab":
            return {
                "50912": "creatinine",
                "50971": "potassium",
                "50983": "sodium",
                "51006": "bun",
                "51222": "hemoglobin",
                "51265": "platelets",
                "51301": "wbc",
            }
        return {}

    def get_unit_conversions(self) -> dict[str, tuple[str, float]]:
        """Get unit conversion factors."""
        return {
            "degF": ("degC", 5 / 9),  # (F - 32) * 5/9
            "mg/dL": ("mmol/L", 0.0555),  # Approximate for glucose
            "mEq/L": ("mmol/L", 1.0),
        }


def create_mimic_iv_adapter(data_dir: str | Path, version: str = "2.2") -> MIMICIVAdapter:
    """Convenience function to create a MIMIC-IV adapter."""
    config = AdapterConfig(
        data_dir=Path(data_dir),
        version=version,
    )
    return MIMICIVAdapter(config)
