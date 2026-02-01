<!--
PATH: README.md
PURPOSE: Public repository for Rubric Gates (rubrics + schemas + verifier + reproducibility harness).
WHY: Enable credible third-party verification and research reproduction without exposing MedTWIN’s
     proprietary agentic generation/metacognition/refinement IP.

FLOW:
┌───────────────────────────┐   ┌─────────────────────────┐   ┌───────────────────────────┐
│ Define rubrics + schemas  │──▶│ Produce certificates     │──▶│ Verify + reproduce results │
│ (public, versioned)       │   │ (service or harness)     │   │ (public verifier/harness)  │
└───────────────────────────┘   └─────────────────────────┘   └───────────────────────────┘

DEPENDENCIES:
- Python 3.11+
- jsonschema, PyYAML (see pyproject.toml)
-->

# Rubric Gates (public)

Rubric Gates is a **certificate-first gating framework** for trustworthy agentic workflows in medicine.

This repository is intentionally **public and reproducible**, but it is **not** MedTWIN’s proprietary agent
implementation. The contract is the **certificate**: if you can verify the certificate, you can trust the claim.

## What this repo includes (safe to open-source)
- **Rubrics**: Tier 1/2/3 rubric definitions (versioned, auditable)
- **Schemas**: JSON Schemas for certificates and run manifests
- **Verifier**: CLI + library to validate certificate structure and integrity
- **Harness (scaffold)**: a reproducible runner interface (no proprietary agents)
- **Paper workspace**: scope lock + manuscript outline + literature drop zone

## What this repo does NOT include (MedTWIN IP boundary)
- Proprietary **agent generators**, **refiners**, **metacognition implementation**, internal prompts
- Private datasets, internal logs, customer data, or any PHI
- Any “clinical outcome improvement” claims (mortality/LOS/treatment benefit) — out of scope

## Quickstart

### 1) Install (editable)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2) Verify an example certificate
```bash
rubric-gates-verify examples/certificates/example_certificate.json
```

## Repo layout
```text
rubrics/                 # Tiered rubric definitions (public)
schemas/                 # JSON Schemas (certificate, run manifest, rubric)
src/rubric_gates/         # Verifier CLI + core library
examples/                # Example certificates + fixtures
paper/                   # Paper drafts + scope lock + literature notes
```

## Related repositories
- **Quality Gates precedent (paper + implementation)**: `https://github.com/Medtwin-ai/quality-gates-computational-physiology`

## License
MIT (see `LICENSE`).

