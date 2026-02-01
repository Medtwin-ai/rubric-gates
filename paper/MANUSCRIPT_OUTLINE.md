<!--
PATH: paper/MANUSCRIPT_OUTLINE.md
PURPOSE: Manuscript outline with figure/table slots for the Rubric Gates paper.

WHY: Writing should run in parallel with implementation; this outline forces every section to map
     to measurable evidence and reproducible artifacts.
-->

## Title (working)
Rubric Gates: Certificate-First Gating for Provable, Optimizable Agentic Medical Workflows

## 1. Introduction
- Trust failure in medical AI is often epistemic (unverifiable claims) not just model accuracy.
- Contribution: certificates + hierarchical rubrics + governance + measurable evaluation.

## 2. Related Work
- Proof-carrying / certificates
- Model Cards / Datasheets (documentation vs enforcement)
- Constitutional AI / principle-based supervision
- Governance frameworks (NIST AI RMF, PCCP-style change control)
- Calibration / selective prediction (deferral)

## 3. System Overview
- Determinism boundary: propose → spec → execute → certificate.

**Fig 1**: Architecture diagram (gate placement + certificate artifacts).

## 4. Rubric Gates Framework
- Tier 1 constitution (frozen)
- Tier 2 clinical invariants (transferable)
- Tier 3 task benchmarks (reference implementations)
- Gate policy (approve/revise/block) + deferral

**Tbl 1**: Rubric tiers + checks + thresholds.

## 5. Method: Rubric-Gated Refinement (if included)
- Refinement controller driven by rubric failures (keep implementation private; report behavior).

**Fig 2**: Gated refinement loop.

## 6. Data & Database Methodology
- Dataset manifests + adapters + canonical views + deterministic executors.

**Tbl 2**: Dataset × task matrix (anchor vs external validity).

## 7. Experiments
- Baselines B0–B4
- Metrics: soundness/completeness/calibration/repro/cost
- Anti-gaming suite (“passed-but-wrong”)

## 8. Results

**Tbl 3**: Ablation ladder.
**Fig 3**: Calibration + risk–coverage curves.
**Fig 4**: Failure taxonomy by baseline.

## 9. Governance & Drift
- Meta-gate and drift experiment (change-control).

## 10. Discussion + Limitations
- What is guaranteed vs not guaranteed (no outcome claims).
- Threats to validity and extension plan.

