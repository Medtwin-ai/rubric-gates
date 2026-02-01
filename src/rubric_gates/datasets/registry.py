"""
PATH: src/rubric_gates/datasets/registry.py
PURPOSE: Registry of supported datasets for Rubric Gates benchmarks.

WHY: Centralized dataset metadata enables:
     - Automatic version tracking
     - Integrity verification (expected hashes)
     - Adapter discovery
     - Documentation generation

DEPENDENCIES: None (pure Python data structures)
"""

from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class DatasetInfo:
    """Metadata about a supported dataset."""

    id: str
    name: str
    description: str
    source: str  # PhysioNet URL or other source
    version: str
    credentialed: bool  # Requires PhysioNet credentialed access
    license: str
    citation: str
    tables: list[str]  # Key tables in the dataset
    adapter_module: str  # Python module path for adapter
    expected_size_gb: float | None = None
    physionet_project: str | None = None  # For PhysioNet downloads


# ============================================================================
# DATASET REGISTRY
# ============================================================================

DATASET_REGISTRY: dict[str, DatasetInfo] = {}


def register_dataset(info: DatasetInfo) -> None:
    """Register a dataset in the global registry."""
    DATASET_REGISTRY[info.id] = info


def get_dataset_info(dataset_id: str) -> DatasetInfo | None:
    """Get dataset info by ID."""
    return DATASET_REGISTRY.get(dataset_id)


def list_datasets() -> list[DatasetInfo]:
    """List all registered datasets."""
    return list(DATASET_REGISTRY.values())


# ============================================================================
# REGISTERED DATASETS
# ============================================================================

# MIMIC-IV: Medical Information Mart for Intensive Care
register_dataset(
    DatasetInfo(
        id="mimic_iv",
        name="MIMIC-IV",
        description="Critical care database from Beth Israel Deaconess Medical Center (2008-2019)",
        source="https://physionet.org/content/mimiciv/",
        version="2.2",
        credentialed=True,
        license="PhysioNet Credentialed Health Data License 1.5.0",
        citation="Johnson, A., Bulgarelli, L., Pollard, T., Horng, S., Celi, L. A., & Mark, R. (2023). MIMIC-IV (version 2.2). PhysioNet.",
        tables=["patients", "admissions", "icustays", "chartevents", "labevents", "prescriptions", "diagnoses_icd"],
        adapter_module="rubric_gates.adapters.mimic_iv",
        expected_size_gb=7.0,
        physionet_project="mimiciv/2.2",
    )
)

# eICU Collaborative Research Database
register_dataset(
    DatasetInfo(
        id="eicu",
        name="eICU-CRD",
        description="Multi-center critical care database from Philips eICU program (2014-2015)",
        source="https://physionet.org/content/eicu-crd/",
        version="2.0",
        credentialed=True,
        license="PhysioNet Credentialed Health Data License 1.5.0",
        citation="Pollard, T. J., Johnson, A. E. W., Raffa, J. D., Celi, L. A., Mark, R. G., & Badawi, O. (2018). The eICU Collaborative Research Database (version 2.0). PhysioNet.",
        tables=["patient", "admissiondx", "apacheapsvar", "apachepatientresult", "diagnosis", "lab", "medication", "vitalperiodic"],
        adapter_module="rubric_gates.adapters.eicu",
        expected_size_gb=3.5,
        physionet_project="eicu-crd/2.0",
    )
)

# AmsterdamUMCdb
register_dataset(
    DatasetInfo(
        id="amsterdamumcdb",
        name="AmsterdamUMCdb",
        description="Critical care database from Amsterdam University Medical Centers (2003-2016)",
        source="https://physionet.org/content/amsterdamumcdb/",
        version="1.0.2",
        credentialed=True,
        license="Open Data Commons Open Database License v1.0",
        citation="Thoral, P. J., et al. (2021). Sharing ICU Patient Data Responsibly. Critical Care Medicine.",
        tables=["admissions", "drugitems", "freetextitems", "listitems", "numericitems", "procedureorderitems"],
        adapter_module="rubric_gates.adapters.amsterdamumcdb",
        expected_size_gb=1.2,
        physionet_project="amsterdamumcdb/1.0.2",
    )
)

# HiRID (High Time Resolution ICU Dataset)
register_dataset(
    DatasetInfo(
        id="hirid",
        name="HiRID",
        description="High time resolution ICU dataset from Bern University Hospital (2008-2016)",
        source="https://physionet.org/content/hirid/",
        version="1.1.1",
        credentialed=True,
        license="PhysioNet Credentialed Health Data License 1.5.0",
        citation="Hyland, S. L., et al. (2020). Early prediction of circulatory failure in the intensive care unit using machine learning. Nature Medicine.",
        tables=["general_table", "observation_tables", "pharma_records"],
        adapter_module="rubric_gates.adapters.hirid",
        expected_size_gb=35.0,
        physionet_project="hirid/1.1.1",
    )
)

# MIMIC-III (for backward compatibility / comparison)
register_dataset(
    DatasetInfo(
        id="mimic_iii",
        name="MIMIC-III",
        description="Critical care database from Beth Israel Deaconess Medical Center (2001-2012)",
        source="https://physionet.org/content/mimiciii/",
        version="1.4",
        credentialed=True,
        license="PhysioNet Credentialed Health Data License 1.5.0",
        citation="Johnson, A. E. W., et al. (2016). MIMIC-III, a freely accessible critical care database. Scientific Data.",
        tables=["patients", "admissions", "icustays", "chartevents", "labevents", "prescriptions", "diagnoses_icd"],
        adapter_module="rubric_gates.adapters.mimic_iii",
        expected_size_gb=6.0,
        physionet_project="mimiciii/1.4",
    )
)
