-- Employer-facing analysis queries for Maryland Healthcare Access Analytics.

-- 1. Highest risk Maryland jurisdictions.
SELECT
    c.county_name,
    c.region,
    r.access_risk_score,
    r.access_risk_tier,
    r.top_risk_factor
FROM access_risk_scores r
JOIN counties c USING (county_fips)
ORDER BY r.access_risk_score DESC;

-- 2. Jurisdictions with high poverty and high chronic disease burden.
WITH state_average AS (
    SELECT
        AVG(d.poverty_pct) AS poverty_pct,
        AVG(r.chronic_burden_index) AS chronic_burden_index
    FROM demographics d
    JOIN access_risk_scores r USING (county_fips, data_year)
)
SELECT
    c.county_name,
    d.poverty_pct,
    r.chronic_burden_index,
    h.poor_or_fair_health_pct,
    h.diabetes_pct,
    r.access_risk_score
FROM counties c
JOIN demographics d USING (county_fips)
JOIN health_outcomes h USING (county_fips, data_year)
JOIN access_risk_scores r USING (county_fips, data_year)
CROSS JOIN state_average s
WHERE d.poverty_pct > s.poverty_pct
  AND r.chronic_burden_index > s.chronic_burden_index
ORDER BY r.access_risk_score DESC;

-- 3. Jurisdictions with high uninsured rates.
WITH state_average AS (
    SELECT AVG(uninsured_pct) AS uninsured_pct
    FROM demographics
)
SELECT
    c.county_name,
    d.uninsured_pct,
    r.insurance_access_burden_index,
    r.access_risk_score
FROM counties c
JOIN demographics d USING (county_fips)
JOIN access_risk_scores r USING (county_fips, data_year)
CROSS JOIN state_average s
WHERE d.uninsured_pct > s.uninsured_pct
ORDER BY d.uninsured_pct DESC;

-- 4. Jurisdictions with provider shortage burden.
SELECT
    c.county_name,
    p.hpsa_primary_care_score,
    p.hpsa_mental_health_score,
    p.hpsa_dental_score,
    r.provider_gap_index,
    r.access_risk_score
FROM counties c
JOIN provider_shortages p USING (county_fips)
JOIN access_risk_scores r USING (county_fips, data_year)
ORDER BY r.provider_gap_index DESC;

-- 5. Jurisdictions with weak hospital access or quality indicators.
SELECT
    c.county_name,
    h.hospital_count,
    h.acute_care_hospitals,
    h.emergency_services_count,
    h.avg_hospital_star_rating,
    r.hospital_quality_gap_index,
    r.access_risk_score
FROM counties c
JOIN hospital_quality h USING (county_fips)
JOIN access_risk_scores r USING (county_fips, data_year)
ORDER BY r.hospital_quality_gap_index DESC;

-- 6. Jurisdictions above Maryland average on multiple burden indicators.
WITH state_average AS (
    SELECT
        AVG(d.poverty_pct) AS poverty_pct,
        AVG(d.uninsured_pct) AS uninsured_pct,
        AVG(h.poor_or_fair_health_pct) AS poor_or_fair_health_pct,
        AVG(r.provider_gap_index) AS provider_gap_index,
        AVG(r.access_risk_score) AS access_risk_score
    FROM demographics d
    JOIN health_outcomes h USING (county_fips, data_year)
    JOIN access_risk_scores r USING (county_fips, data_year)
)
SELECT
    c.county_name,
    ROUND(d.poverty_pct - s.poverty_pct, 1) AS poverty_vs_avg,
    ROUND(d.uninsured_pct - s.uninsured_pct, 1) AS uninsured_vs_avg,
    ROUND(h.poor_or_fair_health_pct - s.poor_or_fair_health_pct, 1) AS poor_health_vs_avg,
    ROUND(r.provider_gap_index - s.provider_gap_index, 1) AS provider_gap_vs_avg,
    ROUND(r.access_risk_score - s.access_risk_score, 1) AS risk_score_vs_avg
FROM counties c
JOIN demographics d USING (county_fips)
JOIN health_outcomes h USING (county_fips, data_year)
JOIN access_risk_scores r USING (county_fips, data_year)
CROSS JOIN state_average s
WHERE d.poverty_pct > s.poverty_pct
   OR d.uninsured_pct > s.uninsured_pct
   OR h.poor_or_fair_health_pct > s.poor_or_fair_health_pct
   OR r.provider_gap_index > s.provider_gap_index
ORDER BY risk_score_vs_avg DESC;

-- 7. Risk components by region.
SELECT
    c.region,
    ROUND(AVG(r.access_risk_score), 1) AS avg_access_risk_score,
    ROUND(AVG(r.socioeconomic_need_index), 1) AS avg_socioeconomic_need,
    ROUND(AVG(r.insurance_access_burden_index), 1) AS avg_insurance_access_burden,
    ROUND(AVG(r.chronic_burden_index), 1) AS avg_chronic_burden,
    ROUND(AVG(r.provider_gap_index), 1) AS avg_provider_shortage,
    ROUND(AVG(r.hospital_quality_gap_index), 1) AS avg_hospital_burden
FROM counties c
JOIN access_risk_scores r USING (county_fips)
GROUP BY c.region
ORDER BY avg_access_risk_score DESC;

-- 8. Data completeness by source.
SELECT
    data_mode,
    source_acs,
    source_cdc_places,
    source_hrsa_hpsa,
    source_cms_hospital_quality,
    COUNT(*) AS jurisdictions
FROM source_status
GROUP BY
    data_mode,
    source_acs,
    source_cdc_places,
    source_hrsa_hpsa,
    source_cms_hospital_quality;
