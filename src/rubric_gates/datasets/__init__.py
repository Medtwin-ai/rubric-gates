"""
PATH: src/rubric_gates/datasets/__init__.py
PURPOSE: Dataset management for Rubric Gates benchmarks.

WHY: Reproducible research requires versioned, integrity-checked datasets.
     This module provides infrastructure for downloading, validating, and
     managing clinical datasets from PhysioNet and other sources.
"""

from rubric_gates.datasets.downloader import (
    PhysioNetDownloader,
    download_dataset,
    list_available_datasets,
)
from rubric_gates.datasets.manifest import (
    DatasetManifest,
    create_manifest,
    load_manifest,
    verify_manifest,
)
from rubric_gates.datasets.registry import (
    DATASET_REGISTRY,
    DatasetInfo,
    get_dataset_info,
    register_dataset,
)

__all__ = [
    # Downloader
    "PhysioNetDownloader",
    "download_dataset",
    "list_available_datasets",
    # Manifest
    "DatasetManifest",
    "create_manifest",
    "load_manifest",
    "verify_manifest",
    # Registry
    "DATASET_REGISTRY",
    "DatasetInfo",
    "get_dataset_info",
    "register_dataset",
]
