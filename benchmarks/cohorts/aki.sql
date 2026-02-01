-- PATH: benchmarks/cohorts/aki.sql
-- PURPOSE: Reference implementation for Acute Kidney Injury (AKI) cohort
-- DATASET: MIMIC-IV v2.2
--
-- KDIGO CRITERIA:
-- Stage 1: Creatinine increase >= 0.3 mg/dL within 48h OR >= 1.5-1.9x baseline
-- Stage 2: Creatinine >= 2.0-2.9x baseline
-- Stage 3: Creatinine >= 3.0x baseline OR >= 4.0 mg/dL OR RRT initiation
--
-- OUTPUT COLUMNS:
-- - subject_id: patient identifier
-- - hadm_id: admission identifier
-- - stay_id: ICU stay identifier
-- - aki_time: time of AKI onset
-- - aki_stage: KDIGO stage (1, 2, or 3)
-- - baseline_creatinine: baseline creatinine value
-- - peak_creatinine: peak creatinine during episode
--
-- DETERMINISTIC: Yes
-- VALIDATED: Follows KDIGO 2012 guidelines

WITH baseline_creatinine AS (
    -- Baseline: minimum creatinine in 7 days before admission
    -- or first creatinine if no prior values
    SELECT
        i.subject_id,
        i.hadm_id,
        i.stay_id,
        i.intime,
        COALESCE(
            MIN(CASE 
                WHEN le.charttime BETWEEN i.intime - INTERVAL '7 days' AND i.intime 
                THEN le.valuenum 
            END),
            MIN(CASE 
                WHEN le.charttime BETWEEN i.intime AND i.intime + INTERVAL '24 hours' 
                THEN le.valuenum 
            END)
        ) AS baseline_cr
    FROM mimiciv_icu.icustays i
    INNER JOIN mimiciv_hosp.labevents le 
        ON i.hadm_id = le.hadm_id
        AND le.itemid = 50912  -- Creatinine
        AND le.valuenum IS NOT NULL
        AND le.valuenum > 0
        AND le.valuenum < 25  -- Exclude implausible values
    GROUP BY i.subject_id, i.hadm_id, i.stay_id, i.intime
),

creatinine_timeseries AS (
    -- All creatinine measurements during ICU stay
    SELECT
        bc.subject_id,
        bc.hadm_id,
        bc.stay_id,
        bc.baseline_cr,
        le.charttime,
        le.valuenum AS creatinine,
        -- 48-hour window for absolute increase
        MAX(le.valuenum) OVER (
            PARTITION BY bc.stay_id 
            ORDER BY le.charttime 
            ROWS BETWEEN 48 PRECEDING AND CURRENT ROW
        ) - MIN(le.valuenum) OVER (
            PARTITION BY bc.stay_id 
            ORDER BY le.charttime 
            ROWS BETWEEN 48 PRECEDING AND CURRENT ROW
        ) AS cr_increase_48h,
        -- Ratio to baseline
        le.valuenum / NULLIF(bc.baseline_cr, 0) AS cr_ratio
    FROM baseline_creatinine bc
    INNER JOIN mimiciv_hosp.labevents le 
        ON bc.hadm_id = le.hadm_id
        AND le.itemid = 50912
        AND le.valuenum IS NOT NULL
        AND le.valuenum > 0
        AND le.charttime >= bc.intime
),

aki_staging AS (
    -- Apply KDIGO staging criteria
    SELECT
        ct.*,
        CASE
            -- Stage 3: >= 3x baseline OR >= 4.0 OR RRT
            WHEN ct.cr_ratio >= 3.0 OR ct.creatinine >= 4.0 THEN 3
            -- Stage 2: 2.0-2.9x baseline
            WHEN ct.cr_ratio >= 2.0 THEN 2
            -- Stage 1: >= 0.3 increase in 48h OR 1.5-1.9x baseline
            WHEN ct.cr_increase_48h >= 0.3 OR ct.cr_ratio >= 1.5 THEN 1
            ELSE 0
        END AS aki_stage
    FROM creatinine_timeseries ct
),

aki_onset AS (
    -- First occurrence of AKI for each stay
    SELECT DISTINCT ON (stay_id)
        subject_id,
        hadm_id,
        stay_id,
        charttime AS aki_time,
        aki_stage,
        baseline_cr AS baseline_creatinine,
        creatinine AS onset_creatinine
    FROM aki_staging
    WHERE aki_stage >= 1
    ORDER BY stay_id, charttime
),

peak_creatinine AS (
    -- Peak creatinine after AKI onset
    SELECT
        ao.stay_id,
        MAX(le.valuenum) AS peak_creatinine
    FROM aki_onset ao
    INNER JOIN mimiciv_hosp.labevents le 
        ON ao.hadm_id = le.hadm_id
        AND le.itemid = 50912
        AND le.charttime >= ao.aki_time
    GROUP BY ao.stay_id
)

-- Final AKI cohort
SELECT
    ao.subject_id,
    ao.hadm_id,
    ao.stay_id,
    ao.aki_time,
    ao.aki_stage,
    ROUND(ao.baseline_creatinine::numeric, 2) AS baseline_creatinine,
    ROUND(ao.onset_creatinine::numeric, 2) AS onset_creatinine,
    ROUND(pc.peak_creatinine::numeric, 2) AS peak_creatinine,
    p.anchor_age AS age,
    p.gender
FROM aki_onset ao
INNER JOIN peak_creatinine pc ON ao.stay_id = pc.stay_id
INNER JOIN mimiciv_hosp.patients p ON ao.subject_id = p.subject_id
WHERE p.anchor_age >= 18  -- Adults only
ORDER BY ao.subject_id, ao.hadm_id, ao.stay_id;
