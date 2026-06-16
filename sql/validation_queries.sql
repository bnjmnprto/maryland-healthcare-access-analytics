-- Validation checks for Maryland Healthcare Access Analytics.

-- 1. Confirm 24 Maryland jurisdictions.
SELECT COUNT(DISTINCT county_fips) AS jurisdiction_count
FROM counties;

-- 2. Confirm Baltimore City is present.
SELECT county_fips, county_name
FROM counties
WHERE county_name = 'Baltimore City';

-- 3. Detect duplicate FIPS rows in final features.
SELECT county_fips, COUNT(*) AS row_count
FROM final_feature_table
GROUP BY county_fips
HAVING COUNT(*) > 1;

-- 4. Detect duplicate county names.
SELECT county_name, COUNT(*) AS row_count
FROM final_feature_table
GROUP BY county_name
HAVING COUNT(*) > 1;

-- 5. Check risk-score range.
SELECT
    MIN(access_risk_score) AS min_risk_score,
    MAX(access_risk_score) AS max_risk_score
FROM access_risk_scores;

-- 6. Source coverage.
SELECT
    source_acs,
    source_cdc_places,
    source_hrsa_hpsa,
    source_cms_hospital_quality,
    COUNT(*) AS jurisdictions
FROM source_status
GROUP BY
    source_acs,
    source_cdc_places,
    source_hrsa_hpsa,
    source_cms_hospital_quality;

-- 7. Missing key feature values.
SELECT
    SUM(CASE WHEN poverty_pct IS NULL THEN 1 ELSE 0 END) AS missing_poverty,
    SUM(CASE WHEN uninsured_pct IS NULL THEN 1 ELSE 0 END) AS missing_uninsured,
    SUM(CASE WHEN poor_or_fair_health_pct IS NULL THEN 1 ELSE 0 END) AS missing_poor_health,
    SUM(CASE WHEN access_risk_tier IS NULL THEN 1 ELSE 0 END) AS missing_risk_tier
FROM final_feature_table;
