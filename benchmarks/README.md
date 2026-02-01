# Benchmark Reference Implementations

This directory contains reference implementations for benchmark tasks used in the Rubric Gates paper.

## Structure

```
benchmarks/
├── cohorts/           # Reference SQL for cohort construction
│   ├── sepsis.sql     # Sepsis-3 cohort (MIMIC-IV)
│   ├── aki.sql        # Acute Kidney Injury cohort (MIMIC-IV)
│   └── mortality.sql  # ICU mortality cohort (coming soon)
├── references/        # Reference outputs for validation
└── README.md
```

## Cohort Definitions

### Sepsis-3 (`cohorts/sepsis.sql`)

**Criteria**: Adult ICU patients meeting Sepsis-3 criteria:
- Suspected infection (antibiotics + cultures within 72h)
- SOFA score ≥ 2

**Output**: `subject_id`, `hadm_id`, `stay_id`, `sepsis_time`, `sofa_score`, `age`, `gender`

**Reference**: Singer M, et al. The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3). JAMA. 2016.

### Acute Kidney Injury (`cohorts/aki.sql`)

**Criteria**: KDIGO staging based on creatinine:
- Stage 1: ≥0.3 mg/dL increase in 48h OR ≥1.5x baseline
- Stage 2: ≥2.0x baseline
- Stage 3: ≥3.0x baseline OR ≥4.0 mg/dL OR RRT

**Output**: `subject_id`, `hadm_id`, `stay_id`, `aki_time`, `aki_stage`, `baseline_creatinine`, `peak_creatinine`

**Reference**: KDIGO Clinical Practice Guideline for Acute Kidney Injury. Kidney Int Suppl. 2012.

## Usage

These SQL queries are designed for execution against MIMIC-IV in a DuckDB environment:

```python
import duckdb

conn = duckdb.connect()
conn.execute("ATTACH 'mimic_iv.duckdb' AS mimiciv")

with open('benchmarks/cohorts/sepsis.sql') as f:
    sql = f.read()

cohort = conn.execute(sql).fetchdf()
print(f"Sepsis cohort: {len(cohort)} patients")
```

## Validation

Reference cohorts are validated against:
1. Published cohort sizes from literature
2. MIMIC Code Repository implementations
3. Manual chart review (sample)

## Adding New References

1. Create SQL file in `cohorts/` with header documenting:
   - Criteria
   - Output columns
   - Literature reference
   - Validation status

2. Ensure SQL is deterministic (no random elements)

3. Add entry to this README

## License

Reference implementations are provided under MIT license for research purposes.
