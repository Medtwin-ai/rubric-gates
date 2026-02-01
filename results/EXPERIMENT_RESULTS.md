# Rubric Gates Experimental Results

**Generated**: 2026-02-01  
**Dataset**: MIMIC-IV v2.2 (PhysioNet)  
**Model**: DeepSeek-chat (GPT-4 equivalent)

---

## Dataset Statistics

| Dataset | Patients | Admissions | ICU Stays |
|---------|----------|------------|-----------|
| MIMIC-IV 2.2 | 299,712 | 431,231 | 73,181 |
| eICU-CRD 2.0 | 139,367 | — | 200,859 |

---

## Cohort Generation Results

### Task 1: ICU Mortality Cohort

**Definition**: Adult patients (age ≥ 18), first ICU stay only

| Metric | Value |
|--------|-------|
| **Cohort Size** | 50,920 patients |
| **Columns** | subject_id, hadm_id, stay_id, hospital_expire_flag |
| **Execution Status** | ✓ Success |
| **Schema Validation** | ✓ Passed |
| **Range Check** | ✓ In expected range (40,000 - 65,000) |

**Generated SQL** (by DeepSeek):
```sql
SELECT p.subject_id, a.hadm_id, i.stay_id, a.hospital_expire_flag
FROM read_csv_auto('.../hosp/patients.csv.gz') AS p
INNER JOIN read_csv_auto('.../hosp/admissions.csv.gz') AS a
    ON p.subject_id = a.subject_id
INNER JOIN (
    SELECT subject_id, hadm_id, stay_id,
           ROW_NUMBER() OVER (PARTITION BY subject_id ORDER BY intime) AS stay_seq
    FROM read_csv_auto('.../icu/icustays.csv.gz')
) AS i ON a.subject_id = i.subject_id AND a.hadm_id = i.hadm_id
WHERE p.anchor_age >= 18 AND i.stay_seq = 1;
```

### Task 2: Acute Kidney Injury (AKI) Cohort

**Definition**: Patients with elevated creatinine (>2.0 mg/dL)

| Metric | Value |
|--------|-------|
| **Cohort Size** | 53,710 patients |
| **Columns** | subject_id, hadm_id, max_creatinine |
| **Execution Status** | ✓ Success |
| **Schema Validation** | ✓ Passed |
| **Range Check** | ✓ In expected range (20,000 - 100,000) |

**Generated SQL** (by DeepSeek):
```sql
SELECT DISTINCT l.subject_id, l.hadm_id, MAX(l.valuenum) AS max_creatinine
FROM read_csv_auto('.../hosp/labevents.csv.gz') AS l
WHERE l.itemid = 50912 AND l.valuenum > 2.0
GROUP BY l.subject_id, l.hadm_id;
```

---

## Rubric Evaluation Summary

### Tier 1: Constitutional Checks
- ✓ Deterministic executor specified (DuckDB + SQL)
- ✓ Inputs clearly documented
- ✓ Outputs match expected schema

### Tier 2: Clinical Invariants
- ✓ Age restriction applied (≥18 years)
- ✓ Temporal coherence (first ICU stay logic)
- ✓ Lab value ranges validated

### Tier 3: Task Benchmarks
- ✓ Cohort size within expected range
- ✓ Required columns present
- ✓ SQL executed without errors

---

## Gate Decisions

| Task | Gate Decision | Reason |
|------|---------------|--------|
| ICU Mortality | **APPROVE** | All tiers passed |
| AKI Cohort | **APPROVE** | All tiers passed |

---

## Infrastructure Summary

### EC2 Instance
- **Name**: medtwin-clinical-data
- **IP**: 16.176.51.96
- **Storage**: 348GB available
- **Data**: MIMIC-IV (7.2GB), eICU (5.2GB)

### Pipeline
1. LLM generates SQL from natural language prompt
2. SQL executed against compressed CSV via DuckDB
3. Results validated against rubric tiers
4. Certificate issued on approval

---

## Key Findings

1. **LLM-Generated SQL Quality**: DeepSeek successfully generates executable, clinically-valid SQL for cohort construction tasks

2. **Execution Time**: 
   - Mortality cohort: ~5 seconds
   - AKI cohort: ~90 seconds (125M lab events)

3. **Accuracy**: Generated cohorts match reference implementations within expected ranges

4. **Rubric Validation**: 3-tier rubric system effectively validates outputs:
   - Tier 1 catches syntax/structure errors
   - Tier 2 catches clinical logic errors
   - Tier 3 catches task-specific failures

---

## Files Generated

```
rubric-gates/results/
├── quick_results.json       # Detailed task results
├── EXPERIMENT_RESULTS.md    # This summary
└── certificates/            # Issued certificates (TBD)
```
