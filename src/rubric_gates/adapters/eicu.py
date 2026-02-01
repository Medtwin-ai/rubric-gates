"""
PATH: src/rubric_gates/adapters/eicu.py
PURPOSE: Adapter for eICU Collaborative Research Database.

eICU SCHEMA NOTES:
- patient.csv: Demographics and admission info (uniquepid, patientunitstayid)
- admissiondx.csv: Admission diagnoses
- apacheapsvar.csv: APACHE variables
- lab.csv: Laboratory measurements
- vitalperiodic.csv: Vital signs (5-minute intervals)
- medication.csv: Medications

TEMPORAL NOTES:
- eICU uses offset times in minutes from unit admission
- hospitaladmitoffset: minutes from hospital admission to unit admission
- All times are relative, not absolute

DIFFERENCES FROM MIMIC:
- Multi-center data (208 hospitals)
- Different time representation (offsets vs timestamps)
- Different variable naming conventions
- APACHE scoring available

DEPENDENCIES:
- pandas (for CSV loading)
- duckdb (for SQL execution)
"""

from __future__ import annotations

import gzip
from datetime import datetime, timedelta
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


class EICUAdapter(BaseAdapter):
    """
    Adapter for eICU-CRD v2.0 dataset.

    Expected directory structure:
        data_dir/
        ├── patient.csv.gz
        ├── admissiondx.csv.gz
        ├── apacheapsvar.csv.gz
        ├── lab.csv.gz
        ├── vitalperiodic.csv.gz
        ├── medication.csv.gz
        └── diagnosis.csv.gz
    """

    # Reference time for offset calculations
    _REFERENCE_TIME = datetime(2014, 1, 1, 0, 0, 0)

    @property
    def dataset_id(self) -> str:
        return "eicu"

    @property
    def dataset_name(self) -> str:
        return "eICU-CRD"

    def _read_csv(self, filename: str) -> list[dict[str, Any]]:
        """Read a CSV file (gzipped or plain) from the dataset."""
        # Try gzipped first
        gz_path = self.config.data_dir / f"{filename}.csv.gz"
        if gz_path.exists():
            import csv
            import io

            with gzip.open(gz_path, "rt", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)

        # Try plain CSV
        csv_path = self.config.data_dir / f"{filename}.csv"
        if csv_path.exists():
            import csv

            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)

        raise FileNotFoundError(f"Could not find {filename}.csv or {filename}.csv.gz")

    def _offset_to_datetime(self, offset_minutes: int | str | None) -> datetime | None:
        """Convert eICU offset (minutes from unit admission) to datetime."""
        if offset_minutes is None or offset_minutes == "":
            return None
        try:
            offset = int(float(offset_minutes))
            return self._REFERENCE_TIME + timedelta(minutes=offset)
        except (ValueError, TypeError):
            return None

    def load_patients(self) -> list[PatientRecord]:
        """Load patient demographics from patient.csv."""
        rows = self._read_csv("patient")

        patients = []
        seen_patients = set()

        for row in rows:
            patient_id = row.get("uniquepid") or row.get("patientunitstayid")
            if patient_id in seen_patients:
                continue
            seen_patients.add(patient_id)

            # Parse age (eICU uses "> 89" for ages over 89)
            age_str = row.get("age", "")
            if age_str == "> 89":
                age = 90
            else:
                try:
                    age = int(age_str) if age_str else None
                except ValueError:
                    age = None

            patients.append(
                PatientRecord(
                    patient_id=patient_id,
                    gender=row.get("gender"),
                    anchor_age=age,
                    ethnicity=row.get("ethnicity"),
                )
            )

        return patients

    def load_admissions(self) -> list[AdmissionRecord]:
        """Load admission records from patient.csv."""
        rows = self._read_csv("patient")

        admissions = []
        for row in rows:
            # Calculate times from offsets
            unit_admit_offset = 0  # Reference point
            unit_discharge_offset = row.get("unitdischargeoffset")
            hospital_admit_offset = row.get("hospitaladmitoffset")

            unit_admit_time = self._REFERENCE_TIME
            unit_discharge_time = self._offset_to_datetime(unit_discharge_offset)

            # Hospital admission is before unit admission (negative offset)
            hospital_admit_time = None
            if hospital_admit_offset:
                try:
                    hospital_admit_time = self._REFERENCE_TIME + timedelta(
                        minutes=int(float(hospital_admit_offset))
                    )
                except (ValueError, TypeError):
                    pass

            admissions.append(
                AdmissionRecord(
                    admission_id=row["patientunitstayid"],
                    patient_id=row.get("uniquepid") or row["patientunitstayid"],
                    admit_time=hospital_admit_time or unit_admit_time,
                    discharge_time=unit_discharge_time,
                    death_time=None,  # Would need to check unitdischargestatus
                    admission_type=row.get("unitadmitsource"),
                    admission_location=row.get("hospitaladmitsource"),
                    discharge_location=row.get("unitdischargelocation"),
                    hospital_expire_flag=row.get("unitdischargestatus") == "Expired",
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
        """Load laboratory events from lab.csv."""
        rows = self._read_csv("lab")

        events = []
        for i, row in enumerate(rows):
            # Parse lab value
            value_str = row.get("labresult", "")
            try:
                value_num = float(value_str) if value_str else None
            except ValueError:
                value_num = None

            events.append(
                ClinicalEvent(
                    event_id=f"lab_{i}",
                    patient_id=row["patientunitstayid"],
                    admission_id=row["patientunitstayid"],
                    event_time=self._offset_to_datetime(row.get("labresultoffset")),
                    event_type="lab",
                    item_id=row.get("labname", ""),
                    item_name=row.get("labname", ""),
                    value=row.get("labresult"),
                    value_unit=row.get("labmeasurenamesystem"),
                    value_num=value_num,
                    reference_low=None,
                    reference_high=None,
                )
            )

        return events

    def _load_vital_events(self) -> list[ClinicalEvent]:
        """Load vital sign events from vitalperiodic.csv."""
        rows = self._read_csv("vitalperiodic")

        # Vital sign columns in eICU
        vital_columns = {
            "heartrate": "Heart Rate",
            "respiration": "Respiratory Rate",
            "sao2": "SpO2",
            "temperature": "Temperature",
            "systemicsystolic": "Systolic BP",
            "systemicdiastolic": "Diastolic BP",
            "systemicmean": "Mean BP",
        }

        events = []
        event_idx = 0

        for row in rows:
            offset = row.get("observationoffset")
            event_time = self._offset_to_datetime(offset)

            for col, name in vital_columns.items():
                value_str = row.get(col, "")
                if not value_str or value_str == "":
                    continue

                try:
                    value_num = float(value_str)
                except ValueError:
                    continue

                events.append(
                    ClinicalEvent(
                        event_id=f"vital_{event_idx}",
                        patient_id=row["patientunitstayid"],
                        admission_id=row["patientunitstayid"],
                        event_time=event_time,
                        event_type="vital",
                        item_id=col,
                        item_name=name,
                        value=value_str,
                        value_unit=self._get_vital_unit(col),
                        value_num=value_num,
                    )
                )
                event_idx += 1

        return events

    def _get_vital_unit(self, vital_name: str) -> str:
        """Get the unit for a vital sign."""
        units = {
            "heartrate": "bpm",
            "respiration": "breaths/min",
            "sao2": "%",
            "temperature": "°C",
            "systemicsystolic": "mmHg",
            "systemicdiastolic": "mmHg",
            "systemicmean": "mmHg",
        }
        return units.get(vital_name, "")

    def _load_medication_events(self) -> list[ClinicalEvent]:
        """Load medication events from medication.csv."""
        rows = self._read_csv("medication")

        events = []
        for i, row in enumerate(rows):
            events.append(
                ClinicalEvent(
                    event_id=f"med_{i}",
                    patient_id=row["patientunitstayid"],
                    admission_id=row["patientunitstayid"],
                    event_time=self._offset_to_datetime(row.get("drugstartoffset")),
                    event_type="medication",
                    item_id=row.get("drugname", ""),
                    item_name=row.get("drugname", ""),
                    value=row.get("dosage"),
                    value_unit=row.get("drugunit"),
                )
            )

        return events

    def _load_diagnosis_events(self) -> list[ClinicalEvent]:
        """Load diagnosis events from diagnosis.csv."""
        rows = self._read_csv("diagnosis")

        events = []
        for i, row in enumerate(rows):
            events.append(
                ClinicalEvent(
                    event_id=f"dx_{i}",
                    patient_id=row["patientunitstayid"],
                    admission_id=row["patientunitstayid"],
                    event_time=self._offset_to_datetime(row.get("diagnosisoffset")),
                    event_type="diagnosis",
                    item_id=row.get("icd9code", row.get("diagnosisstring", "")),
                    item_name=row.get("diagnosisstring", ""),
                    value=row.get("diagnosispriority"),
                )
            )

        return events

    def get_cohort_sql(self, criteria: CohortCriteria) -> str:
        """
        Generate DuckDB SQL for cohort selection.

        Note: eICU uses different column names than MIMIC.
        """
        where_clauses = []

        if criteria.min_age is not None:
            # Handle "> 89" age values
            where_clauses.append(
                f"(CASE WHEN age = '> 89' THEN 90 ELSE CAST(age AS INTEGER) END) >= {criteria.min_age}"
            )
        if criteria.max_age is not None:
            where_clauses.append(
                f"(CASE WHEN age = '> 89' THEN 90 ELSE CAST(age AS INTEGER) END) <= {criteria.max_age}"
            )

        if criteria.min_los_hours is not None:
            where_clauses.append(f"unitdischargeoffset / 60.0 >= {criteria.min_los_hours}")
        if criteria.max_los_hours is not None:
            where_clauses.append(f"unitdischargeoffset / 60.0 <= {criteria.max_los_hours}")

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"""
-- eICU-CRD Cohort Selection
-- Generated by rubric-gates EICUAdapter
-- Criteria: {criteria}

SELECT DISTINCT
    uniquepid AS patient_id,
    patientunitstayid AS admission_id,
    gender,
    CASE WHEN age = '> 89' THEN 90 ELSE CAST(age AS INTEGER) END AS age,
    hospitalid,
    unittype,
    unitdischargeoffset / 60.0 AS los_hours,
    CASE WHEN unitdischargestatus = 'Expired' THEN 1 ELSE 0 END AS unit_mortality
FROM patient
WHERE {where_clause}
ORDER BY uniquepid, patientunitstayid
"""
        return sql.strip()

    def get_item_mapping(self, item_type: str) -> dict[str, str]:
        """Get eICU item name to canonical name mapping."""
        if item_type == "vital":
            return {
                "heartrate": "heart_rate",
                "respiration": "respiratory_rate",
                "sao2": "spo2",
                "temperature": "temperature_c",
                "systemicsystolic": "sbp_nibp",
                "systemicdiastolic": "dbp_nibp",
                "systemicmean": "map_nibp",
            }
        elif item_type == "lab":
            return {
                "creatinine": "creatinine",
                "potassium": "potassium",
                "sodium": "sodium",
                "BUN": "bun",
                "Hgb": "hemoglobin",
                "platelets x 1000": "platelets",
                "WBC x 1000": "wbc",
            }
        return {}

    def get_unit_conversions(self) -> dict[str, tuple[str, float]]:
        """Get unit conversion factors."""
        return {
            "mg/dl": ("mg/dL", 1.0),
            "mEq/L": ("mmol/L", 1.0),
            "K/uL": ("K/uL", 1.0),
        }


def create_eicu_adapter(data_dir: str | Path, version: str = "2.0") -> EICUAdapter:
    """Convenience function to create an eICU adapter."""
    config = AdapterConfig(
        data_dir=Path(data_dir),
        version=version,
    )
    return EICUAdapter(config)
