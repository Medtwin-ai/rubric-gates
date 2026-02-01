"""
PATH: src/rubric_gates/datasets/manifest.py
PURPOSE: Dataset manifest creation and verification.

WHY: Manifests provide:
     - Cryptographic proof of dataset contents
     - Version tracking for reproducibility
     - Audit trail for regulatory compliance

FLOW:
┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│ Scan dataset files   │──▶│ Compute hashes + stats   │──▶│ Write versioned manifest │
└──────────────────────┘   └──────────────────────────┘   └──────────────────────────┘

DEPENDENCIES:
- hashlib
- json
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclasses.dataclass
class FileInfo:
    """Information about a single file in the dataset."""

    path: str
    size_bytes: int
    sha256: str
    modified_at: str


@dataclasses.dataclass
class DatasetManifest:
    """Complete manifest for a dataset."""

    dataset_id: str
    version: str
    created_at: str
    created_by: str
    source: str
    total_files: int
    total_size_bytes: int
    root_hash: str  # Merkle root of all file hashes
    files: list[FileInfo]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "$schema": "https://github.com/Medtwin-ai/rubric-gates/schemas/dataset_manifest.schema.json",
            "dataset_id": self.dataset_id,
            "version": self.version,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "source": self.source,
            "total_files": self.total_files,
            "total_size_bytes": self.total_size_bytes,
            "root_hash": self.root_hash,
            "files": [
                {
                    "path": f.path,
                    "size_bytes": f.size_bytes,
                    "sha256": f.sha256,
                    "modified_at": f.modified_at,
                }
                for f in self.files
            ],
            "metadata": self.metadata,
        }

    def save(self, path: Path) -> None:
        """Save manifest to JSON file."""
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatasetManifest":
        """Load manifest from dictionary."""
        files = [
            FileInfo(
                path=f["path"],
                size_bytes=f["size_bytes"],
                sha256=f["sha256"],
                modified_at=f["modified_at"],
            )
            for f in data.get("files", [])
        ]
        return cls(
            dataset_id=data["dataset_id"],
            version=data["version"],
            created_at=data["created_at"],
            created_by=data.get("created_by", "unknown"),
            source=data.get("source", ""),
            total_files=data["total_files"],
            total_size_bytes=data["total_size_bytes"],
            root_hash=data["root_hash"],
            files=files,
            metadata=data.get("metadata", {}),
        )


def _compute_sha256(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _compute_merkle_root(hashes: list[str]) -> str:
    """Compute Merkle root from list of hashes."""
    if not hashes:
        return hashlib.sha256(b"").hexdigest()

    # Sort hashes for determinism
    sorted_hashes = sorted(hashes)

    # Build Merkle tree
    while len(sorted_hashes) > 1:
        next_level = []
        for i in range(0, len(sorted_hashes), 2):
            if i + 1 < len(sorted_hashes):
                combined = sorted_hashes[i] + sorted_hashes[i + 1]
            else:
                combined = sorted_hashes[i] + sorted_hashes[i]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        sorted_hashes = next_level

    return sorted_hashes[0]


def create_manifest(
    dataset_dir: Path,
    dataset_id: str,
    version: str,
    source: str = "",
    created_by: str = "rubric-gates",
    metadata: dict[str, Any] | None = None,
    exclude_patterns: list[str] | None = None,
) -> DatasetManifest:
    """
    Create a manifest for a dataset directory.

    Args:
        dataset_dir: Path to the dataset directory
        dataset_id: Dataset identifier
        version: Dataset version
        source: Source URL or description
        created_by: Creator identifier
        metadata: Additional metadata to include
        exclude_patterns: File patterns to exclude (e.g., ["*.log", ".DS_Store"])

    Returns:
        DatasetManifest with file hashes and stats
    """
    dataset_dir = Path(dataset_dir)
    if not dataset_dir.exists():
        raise ValueError(f"Dataset directory does not exist: {dataset_dir}")

    exclude_patterns = exclude_patterns or [".DS_Store", "*.log", "__pycache__"]
    metadata = metadata or {}

    files: list[FileInfo] = []
    total_size = 0

    for file_path in sorted(dataset_dir.rglob("*")):
        if not file_path.is_file():
            continue

        # Check exclusions
        skip = False
        for pattern in exclude_patterns:
            if file_path.match(pattern):
                skip = True
                break
        if skip:
            continue

        # Compute file info
        rel_path = file_path.relative_to(dataset_dir)
        stat = file_path.stat()
        file_hash = _compute_sha256(file_path)

        files.append(
            FileInfo(
                path=str(rel_path),
                size_bytes=stat.st_size,
                sha256=file_hash,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        )
        total_size += stat.st_size

    # Compute Merkle root
    all_hashes = [f.sha256 for f in files]
    root_hash = _compute_merkle_root(all_hashes)

    return DatasetManifest(
        dataset_id=dataset_id,
        version=version,
        created_at=datetime.now(timezone.utc).isoformat(),
        created_by=created_by,
        source=source,
        total_files=len(files),
        total_size_bytes=total_size,
        root_hash=root_hash,
        files=files,
        metadata=metadata,
    )


def load_manifest(path: Path) -> DatasetManifest:
    """Load a manifest from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return DatasetManifest.from_dict(data)


def verify_manifest(manifest: DatasetManifest, dataset_dir: Path) -> tuple[bool, list[str]]:
    """
    Verify a dataset against its manifest.

    Args:
        manifest: The manifest to verify against
        dataset_dir: Path to the dataset directory

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors: list[str] = []
    dataset_dir = Path(dataset_dir)

    for file_info in manifest.files:
        file_path = dataset_dir / file_info.path

        if not file_path.exists():
            errors.append(f"Missing file: {file_info.path}")
            continue

        actual_size = file_path.stat().st_size
        if actual_size != file_info.size_bytes:
            errors.append(f"Size mismatch for {file_info.path}: expected {file_info.size_bytes}, got {actual_size}")
            continue

        actual_hash = _compute_sha256(file_path)
        if actual_hash != file_info.sha256:
            errors.append(f"Hash mismatch for {file_info.path}")

    # Verify Merkle root
    current_hashes = []
    for file_info in manifest.files:
        file_path = dataset_dir / file_info.path
        if file_path.exists():
            current_hashes.append(_compute_sha256(file_path))

    current_root = _compute_merkle_root(current_hashes)
    if current_root != manifest.root_hash:
        errors.append(f"Merkle root mismatch: expected {manifest.root_hash}, got {current_root}")

    return len(errors) == 0, errors
