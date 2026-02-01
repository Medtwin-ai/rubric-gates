# Rubric Gates

[![CI](https://github.com/Medtwin-ai/rubric-gates/actions/workflows/ci.yml/badge.svg)](https://github.com/Medtwin-ai/rubric-gates/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Certificate-first rubric gating for provable, optimizable agentic medical workflows.**

Rubric Gates is a validation framework that ensures AI-generated clinical research artifacts are auditable, reproducible, and benchmark-aligned. Every output ships with a **certificate**—a machine-checkable proof that it passed hierarchical rubric checks.

## Key Features

- **Hierarchical Rubrics**: Tier 1 (constitution) → Tier 2 (clinical invariants) → Tier 3 (task benchmarks)
- **Certificates**: JSON artifacts proving gate decisions with full provenance
- **Reproducibility**: Manifested datasets, versioned rubrics, deterministic execution
- **Open Verification**: Anyone can verify certificates without proprietary code

## Installation

```bash
pip install git+https://github.com/Medtwin-ai/rubric-gates.git
```

## Quick Start

### 1. View Available Rubrics

```bash
rubric-gates info
```

Output:
```
Rubric Gates - Loaded Rubrics

Tier 1:
  📋 tier1.constitution v1.0.0
     Checks (4): determinism, audit trace, PHI protection, outcome claims

Tier 2:
  📋 tier2.clinical_invariants v1.0.0
     Checks (4): unit consistency, plausible ranges, temporal coherence, leakage

Tier 3:
  📋 tier3.cohort_construction v1.0.0
     Checks (2): SQL executes, cohort overlap Jaccard
```

### 2. Evaluate an Artifact

```bash
rubric-gates evaluate artifact.json --context context.json -o certificate.json
```

Example artifact.json:
```json
{
  "type": "cohort_spec",
  "version": "1.0.0",
  "hash": "sha256:abc123...",
  "deterministic_executor": "duckdb+sql"
}
```

### 3. Verify a Certificate

```bash
rubric-gates verify certificate.json
```

Output:
```
✅ Certificate is valid
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RUBRIC GATES SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │   Propose    │───▶│     Spec     │───▶│   Execute    │───▶│ Certificate│ │
│  │  (AI Agent)  │    │ (Versioned)  │    │(Deterministic│    │  (Proof)   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └────────────┘ │
│                                                   │                          │
│                                                   ▼                          │
│                              ┌────────────────────────────────┐              │
│                              │       RUBRIC EVALUATOR          │              │
│                              │  ┌──────┐ ┌──────┐ ┌──────┐   │              │
│                              │  │Tier 1│→│Tier 2│→│Tier 3│   │              │
│                              │  └──────┘ └──────┘ └──────┘   │              │
│                              │              ↓                  │              │
│                              │    approve / revise / block    │              │
│                              └────────────────────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Rubric Tiers

| Tier | Scope | Example Checks | Gate Policy |
|------|-------|----------------|-------------|
| **1: Constitution** | Universal | Determinism, audit trace, no PHI | Block |
| **2: Clinical** | Domain | Unit consistency, plausible ranges | Block/Revise |
| **3: Benchmark** | Task | SQL executes, Jaccard ≥ 0.7 | Revise |

## Dataset Support

```bash
# List available datasets
rubric-gates datasets

# Download from PhysioNet (requires credentials)
export PHYSIONET_USER=your_username
export PHYSIONET_PASS=your_password
rubric-gates download mimic_iv

# Create integrity manifest
rubric-gates manifest create ./datasets/mimic_iv --dataset-id mimic_iv --version 2.2
```

Supported datasets:
- **MIMIC-IV** (v2.2) - Beth Israel Deaconess Medical Center
- **eICU-CRD** (v2.0) - Multi-center Philips eICU
- **AmsterdamUMCdb** (v1.0.2) - Amsterdam University Medical Centers
- **HiRID** (v1.1.1) - Bern University Hospital

## Python API

```python
from rubric_gates import RubricEvaluator, create_certificate

# Create evaluator
evaluator = RubricEvaluator()

# Define artifact
artifact = {
    "type": "cohort_spec",
    "version": "1.0.0",
    "hash": "sha256:abc123",
    "deterministic_executor": "duckdb+sql",
}

# Add context
context = {
    "provenance": {"audit_trace_id": "trace_001"},
    "index_time": "2024-01-01T00:00:00Z",
    "sql_executed": True,
    "cohort_jaccard": 0.85,
}

# Evaluate
result = evaluator.evaluate(artifact, context)
print(f"Decision: {result.gate_decision.decision}")

# Create certificate
certificate = create_certificate(artifact, result, context.get("provenance", {}))
```

## Benchmark Harness

Run reproducible evaluations across datasets:

```python
from rubric_gates import BenchmarkHarness, create_run_config

# Configure run
config = create_run_config(
    datasets=[
        {"id": "mimic_iv", "name": "MIMIC-IV", "source": "physionet", "version": "2.2"},
    ],
    output_dir="./runs",
)

# Run benchmark
harness = BenchmarkHarness(config)
result = harness.run(artifact_generator_function)

print(f"Pass rate: {result.summary['pass_rate']:.1%}")
```

## Project Structure

```
rubric-gates/
├── src/rubric_gates/
│   ├── __init__.py         # Package exports
│   ├── cli.py              # CLI entry point
│   ├── evaluator.py        # Core evaluation logic
│   ├── rubric_loader.py    # YAML rubric loading
│   ├── verify.py           # Certificate verification
│   ├── harness.py          # Benchmark harness
│   ├── adapters/           # Dataset adapters
│   │   ├── base.py         # Base adapter class
│   │   └── mimic_iv.py     # MIMIC-IV adapter
│   └── datasets/           # Dataset management
│       ├── registry.py     # Dataset registry
│       ├── downloader.py   # PhysioNet downloader
│       └── manifest.py     # Integrity manifests
├── rubrics/                # Rubric definitions (YAML)
│   ├── tier1/
│   ├── tier2/
│   └── tier3/
├── schemas/                # JSON schemas
├── paper/                  # Research paper
│   └── latex/              # LaTeX manuscript
├── examples/               # Usage examples
└── tests/                  # Test suite
```

## IP Boundary

| Component | Open Source | Proprietary |
|-----------|-------------|-------------|
| Rubric definitions | ✅ | |
| Certificate schema | ✅ | |
| Verifier + CLI | ✅ | |
| Benchmark harness | ✅ | |
| Dataset adapters | ✅ | |
| Agent generation | | 🔒 |
| Metacognition | | 🔒 |
| Refinement loops | | 🔒 |

## Related Repositories

- [`rubric-gates-service`](https://github.com/Medtwin-ai/rubric-gates-service) (Private) - API service
- [`developers-portal`](https://github.com/Medtwin-ai/developers-portal) - Developer documentation

## Research Paper

The accompanying research paper is in `paper/latex/`. It includes:
- Full methodology for hierarchical rubrics
- Benchmark results across PhysioNet datasets
- Governance and drift detection protocols

**AI Disclosure**: The paper was drafted with LLM assistance. See `paper/latex/main.tex` for the full transparency statement.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `pytest`
4. Run linter: `ruff check src/`
5. Submit a pull request

## License

MIT License. See [LICENSE](LICENSE) for details.

## Citation

```bibtex
@software{rubric_gates_2026,
  title = {Rubric Gates: Certificate-First Gating for Agentic Medical Workflows},
  author = {MedTWIN AI},
  year = {2026},
  url = {https://github.com/Medtwin-ai/rubric-gates}
}
```
