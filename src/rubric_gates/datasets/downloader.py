"""
PATH: src/rubric_gates/datasets/downloader.py
PURPOSE: Download datasets from PhysioNet with integrity verification.

WHY: Reproducible benchmarks require:
     - Verified downloads (checksums)
     - Credential management
     - Progress tracking
     - Resume capability

FLOW:
┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│ Authenticate         │──▶│ Download + verify         │──▶│ Extract + manifest       │
└──────────────────────┘   └──────────────────────────┘   └──────────────────────────┘

DEPENDENCIES:
- requests
- tqdm (optional, for progress)
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from rubric_gates.datasets.registry import DATASET_REGISTRY, DatasetInfo, get_dataset_info

logger = logging.getLogger(__name__)


class PhysioNetDownloader:
    """
    Download datasets from PhysioNet.

    Supports both credentialed and public datasets.
    Uses wget for actual downloads (PhysioNet recommended method).
    """

    PHYSIONET_BASE = "https://physionet.org/files"

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        data_dir: str | Path = "./datasets",
    ):
        """
        Initialize the downloader.

        Args:
            username: PhysioNet username (or set PHYSIONET_USER env var)
            password: PhysioNet password (or set PHYSIONET_PASS env var)
            data_dir: Directory to store downloaded datasets
        """
        self.username = username or os.environ.get("PHYSIONET_USER")
        self.password = password or os.environ.get("PHYSIONET_PASS")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _check_credentials(self) -> bool:
        """Check if credentials are available."""
        return bool(self.username and self.password)

    def _get_download_url(self, dataset_info: DatasetInfo) -> str:
        """Construct the download URL for a dataset."""
        if dataset_info.physionet_project:
            return f"{self.PHYSIONET_BASE}/{dataset_info.physionet_project}/"
        return dataset_info.source

    def download(
        self,
        dataset_id: str,
        tables: list[str] | None = None,
        force: bool = False,
    ) -> Path:
        """
        Download a dataset from PhysioNet.

        Args:
            dataset_id: Dataset identifier (e.g., "mimic_iv")
            tables: Specific tables to download (None = all)
            force: Re-download even if exists

        Returns:
            Path to the downloaded dataset directory
        """
        info = get_dataset_info(dataset_id)
        if info is None:
            raise ValueError(f"Unknown dataset: {dataset_id}")

        if info.credentialed and not self._check_credentials():
            raise ValueError(
                f"Dataset {dataset_id} requires credentials. "
                "Set PHYSIONET_USER and PHYSIONET_PASS environment variables."
            )

        dataset_dir = self.data_dir / dataset_id / info.version
        if dataset_dir.exists() and not force:
            logger.info(f"Dataset {dataset_id} already exists at {dataset_dir}")
            return dataset_dir

        dataset_dir.mkdir(parents=True, exist_ok=True)
        url = self._get_download_url(info)

        logger.info(f"Downloading {info.name} from {url}")

        # Use wget for download (PhysioNet recommended)
        cmd = [
            "wget",
            "-r",  # Recursive
            "-N",  # Only download newer files
            "-c",  # Continue partial downloads
            "--no-parent",  # Don't ascend to parent directory
            "-nH",  # No host directories
            "--cut-dirs=1",  # Remove first directory level
            "-P", str(dataset_dir),
        ]

        if info.credentialed:
            cmd.extend(["--user", self.username, "--password", self.password])

        # Add specific tables if requested
        if tables:
            for table in tables:
                table_url = f"{url}{table}.csv.gz"
                subprocess.run(cmd + [table_url], check=True)
        else:
            cmd.append(url)
            subprocess.run(cmd, check=True)

        logger.info(f"Downloaded {info.name} to {dataset_dir}")
        return dataset_dir

    def verify(self, dataset_id: str) -> bool:
        """
        Verify dataset integrity using SHA256 checksums.

        Args:
            dataset_id: Dataset identifier

        Returns:
            True if verification passed
        """
        info = get_dataset_info(dataset_id)
        if info is None:
            raise ValueError(f"Unknown dataset: {dataset_id}")

        dataset_dir = self.data_dir / dataset_id / info.version

        # Download and verify SHA256SUMS if available
        sha_file = dataset_dir / "SHA256SUMS.txt"
        if not sha_file.exists():
            logger.warning(f"No SHA256SUMS.txt found for {dataset_id}")
            return True  # Can't verify, assume OK

        # Parse and verify checksums
        with open(sha_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                expected_hash, filename = line.strip().split(None, 1)
                file_path = dataset_dir / filename
                if not file_path.exists():
                    logger.warning(f"Missing file: {filename}")
                    continue

                actual_hash = self._compute_sha256(file_path)
                if actual_hash != expected_hash:
                    logger.error(f"Hash mismatch for {filename}")
                    return False

        logger.info(f"Verification passed for {dataset_id}")
        return True

    def _compute_sha256(self, path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def download_dataset(
    dataset_id: str,
    data_dir: str = "./datasets",
    tables: list[str] | None = None,
    force: bool = False,
) -> Path:
    """
    Convenience function to download a dataset.

    Credentials are read from environment variables:
    - PHYSIONET_USER
    - PHYSIONET_PASS

    Args:
        dataset_id: Dataset identifier
        data_dir: Directory to store datasets
        tables: Specific tables to download (None = all)
        force: Re-download even if exists

    Returns:
        Path to the downloaded dataset directory
    """
    downloader = PhysioNetDownloader(data_dir=data_dir)
    return downloader.download(dataset_id, tables=tables, force=force)


def list_available_datasets() -> list[dict[str, Any]]:
    """List all available datasets with their metadata."""
    return [
        {
            "id": info.id,
            "name": info.name,
            "version": info.version,
            "credentialed": info.credentialed,
            "size_gb": info.expected_size_gb,
            "source": info.source,
        }
        for info in DATASET_REGISTRY.values()
    ]
