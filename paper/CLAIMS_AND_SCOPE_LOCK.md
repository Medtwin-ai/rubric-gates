<!--
PATH: paper/CLAIMS_AND_SCOPE_LOCK.md
PURPOSE: Frozen scope + claims discipline for the Rubric Gates paper and public artifacts.

WHY: Prevent “marketing drift”. Every claim must map to a metric + dataset/task + reproducible run manifest.
-->

## Scope lock (frozen)

### In scope
- Certificates as the unit of trust (schema + verifier + artifact hashes)
- Hierarchical rubrics (Tier 1 constitution → Tier 2 clinical invariants → Tier 3 task benchmarks)
- Gate policy (approve / revise / block) with required fixes + deferral
- Deterministic executors (SQL/Python) with manifests + seeds
- Benchmark suite (anchor + external validity)
- Metrics: soundness vs completeness, calibration/deferral, reproducibility, cost
- Governed change control (meta-gates for rubric updates; drift measurement)

### Out of scope (forbidden claims)
- Any clinical outcome improvement claims (mortality, LOS, treatment benefit)
- Medical advice / patient-level decision making claims
- “FDA-approved / regulator-approved” claims unless formally evidenced
- Physiological correctness guarantees beyond the stated gate checks

## Claims discipline (“no bullshit” rules)
- No metric without uncertainty (CI)
- No “better” without ablations (B0–B4) and a failure taxonomy
- No result without a run manifest (dataset manifest + adapter version + rubric versions + seed)
- Always report false accepts (“passed-but-wrong”) and false blocks
- No moving goalposts: thresholds/gate policies are versioned and pre-committed

## Claim → evidence map (locked until earned)

| Claim | Evidence required | Status |
|---|---|---|
| Rubric-gated refinement reduces critical failures vs baselines | Ablation table + failure taxonomy plots on anchor datasets | LOCKED |
| Rubric scores improve calibration and safe deferral | Calibration + risk–coverage curves with protocol + CI | LOCKED |
| Tier 2 transfers across datasets better than task-only rubrics | Transfer experiments across anchors + external validity | LOCKED |
| Governance meta-gates prevent evaluator drift | Drift experiment under change-control with soundness preserved | LOCKED |
| One-command reproducibility regenerates figures/tables | Clean-machine rerun + verifier passing | LOCKED |

