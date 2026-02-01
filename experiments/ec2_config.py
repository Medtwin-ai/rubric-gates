"""
PATH: experiments/ec2_config.py
PURPOSE: Configuration for EC2-based experiment infrastructure.

EC2 INSTANCE: medtwin-clinical-data (16.176.51.96)
SSH KEY: ~/.ssh/clinical-data-key.pem

DATASETS AVAILABLE:
- MIMIC-IV 2.2: /opt/clinical_data/mimic-iv-full/2.2/
- eICU-CRD 2.0: /opt/clinical_data/eicu-crd-full/2.0/
- MIMIC-IV-ECG 1.0: /opt/clinical_data/mimic-iv-ecg-full/1.0/

NOTE: Credentials stored in ~/.netrc on EC2 (not in code)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EC2Config:
    """Configuration for the clinical data EC2 instance."""
    
    # Connection details
    host: str = "16.176.51.96"
    user: str = "ubuntu"
    ssh_key_path: str = os.path.expanduser("~/.ssh/clinical-data-key.pem")
    
    # Data paths on EC2
    data_root: str = "/opt/clinical_data"
    
    # Dataset paths (relative to data_root)
    mimic_iv_path: str = "mimic-iv-full/2.2"
    eicu_path: str = "eicu-crd-full/2.0"
    mimic_ecg_path: str = "mimic-iv-ecg-full/1.0"
    
    # Local cache for results
    local_cache: str = os.path.expanduser("~/.rubric-gates/cache")
    
    @property
    def ssh_command_base(self) -> str:
        """Base SSH command for connecting to EC2."""
        return f"ssh -i {self.ssh_key_path} {self.user}@{self.host}"
    
    def get_dataset_path(self, dataset_id: str) -> str:
        """Get full path for a dataset on EC2."""
        paths = {
            "mimic_iv": f"{self.data_root}/{self.mimic_iv_path}",
            "eicu": f"{self.data_root}/{self.eicu_path}",
            "mimic_ecg": f"{self.data_root}/{self.mimic_ecg_path}",
        }
        if dataset_id not in paths:
            raise ValueError(f"Unknown dataset: {dataset_id}. Available: {list(paths.keys())}")
        return paths[dataset_id]


# Default configuration
EC2 = EC2Config()


# Dataset metadata (for reference)
DATASETS = {
    "mimic_iv": {
        "name": "MIMIC-IV",
        "version": "2.2",
        "size_gb": 7.2,
        "tables": ["hosp", "icu"],
        "ec2_path": EC2.get_dataset_path("mimic_iv"),
    },
    "eicu": {
        "name": "eICU-CRD",
        "version": "2.0", 
        "size_gb": 5.2,
        "tables": ["patient", "lab", "vitalperiodic", "medication"],
        "ec2_path": EC2.get_dataset_path("eicu"),
    },
    "mimic_ecg": {
        "name": "MIMIC-IV-ECG",
        "version": "1.0",
        "size_gb": 0.5,
        "tables": ["records"],
        "ec2_path": EC2.get_dataset_path("mimic_ecg"),
    },
}
