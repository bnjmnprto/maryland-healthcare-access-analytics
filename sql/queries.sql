-- 1. Which Maryland counties have the highest healthcare access risk?
SELECT
    c.county_name,
    c.region,
    r.access_risk_score,
    r.access_risk_tier,
    r.high_access_risk
FROM access_risk_scores r
JOIN counties c USING (county_fips)
ORDER BY r.access_risk_score DESC;

-- 2. Which counties combine high poverty, high uninsured rates, and poor provider access?
WITH state_average AS (
    SELECT
        AVG(d.poverty_pct) AS avg_poverty_pct,
        AVG(d.uninsured_pct) AS avg_uninsured_pct,
        AVG(p.provider_access_index) AS avg_provider_access_index
    FROM demographics d
    JOIN provider_shortages p USING (county_fips, data_year)
)
SELECT
    c.county_name,
    d.poverty_pct,
    d.uninsured_pct,
    p.provider_access_index,
    r.access_risk_score
FROM counties c
JOIN demographics d USING (county_fips)
JOIN provider_shortages p USING (county_fips, data_year)
JOIN access_risk_scores r USING (county_fips, data_year)
CROSS JOIN state_average s
WHERE d.poverty_pct > s.avg_poverty_pct
  AND d.uninsured_pct > s.avg_uninsured_pct
  AND p.provider_access_index < s.avg_provider_access_index
ORDER BY r.access_risk_score DESC;

-- 3. Which counties have worse chronic disease burden?
SELECT
    c.county_name,
    h.diabetes_pct,
    h.obesity_pct,
    h.hypertension_pct,
    h.poor_or_fair_health_pct,
    h.preventable_hospital_stays_per_100k,
    r.chronic_burden_index
FROM counties c
JOIN health_outcomes h USING (county_fips)
JOIN access_risk_scores r USING (county_fips, data_year)
ORDER BY r.chronic_burden_index DESC;

-- 4. How do counties compare to the Maryland state average?
WITH state_average AS (
    SELECT
        AVG(d.poverty_pct) AS poverty_pct,
        AVG(d.uninsured_pct) AS uninsured_pct,
        AVG(h.diabetes_pct) AS diabetes_pct,
        AVG(h.poor_or_fair_health_pct) AS poor_or_fair_health_pct,
        AVG(p.provider_access_index) AS provider_access_index,
        AVG(r.access_risk_score) AS access_risk_score
    FROM demographics d
    JOIN health_outcomes h USING (county_fips, data_year)
    JOIN provider_shortages p USING (county_fips, data_year)
    JOIN access_risk_scores r USING (county_fips, data_year)
)
SELECT
    c.county_name,
    ROUND(d.poverty_pct - s.poverty_pct, 1) AS poverty_vs_state_avg,
    ROUND(d.uninsured_pct - s.uninsured_pct, 1) AS uninsured_vs_state_avg,
    ROUND(h.diabetes_pct - s.diabetes_pct, 1) AS diabetes_vs_state_avg,
    ROUND(h.poor_or_fair_health_pct - s.poor_or_fair_health_pct, 1) AS poor_health_vs_state_avg,
    ROUND(p.provider_access_index - s.provider_access_index, 1) AS provider_access_vs_state_avg,
    ROUND(r.access_risk_score - s.access_risk_score, 1) AS risk_score_vs_state_avg
FROM counties c
JOIN demographics d USING (county_fips)
JOIN health_outcomes h USING (county_fips, data_year)
JOIN provider_shortages p USING (county_fips, data_year)
JOIN access_risk_scores r USING (county_fips, data_year)
CROSS JOIN state_average s
ORDER BY risk_score_vs_state_avg DESC;
