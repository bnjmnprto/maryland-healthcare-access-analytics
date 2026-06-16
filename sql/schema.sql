-- SQLite schema for the Maryland Healthcare Access Analytics.
-- The model is intentionally county-level so public datasets can be joined by FIPS code.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS access_risk_scores;
DROP TABLE IF EXISTS model_outputs;
DROP TABLE IF EXISTS source_status;
DROP TABLE IF EXISTS final_feature_table;
DROP TABLE IF EXISTS hospital_quality;
DROP TABLE IF EXISTS provider_shortages;
DROP TABLE IF EXISTS health_outcomes;
DROP TABLE IF EXISTS demographics;
DROP TABLE IF EXISTS counties;

CREATE TABLE counties (
    county_fips TEXT PRIMARY KEY,
    county_name TEXT NOT NULL,
    region TEXT NOT NULL,
    rural_flag INTEGER NOT NULL CHECK (rural_flag IN (0, 1))
);

CREATE TABLE demographics (
    county_fips TEXT NOT NULL,
    data_year INTEGER NOT NULL,
    population INTEGER NOT NULL,
    median_household_income REAL NOT NULL,
    poverty_pct REAL NOT NULL,
    uninsured_pct REAL NOT NULL,
    pct_age_65_plus REAL NOT NULL,
    disability_pct REAL NOT NULL,
    transportation_access_proxy REAL NOT NULL,
    internet_access_gap_pct REAL NOT NULL,
    pct_nonwhite REAL NOT NULL,
    PRIMARY KEY (county_fips, data_year),
    FOREIGN KEY (county_fips) REFERENCES counties(county_fips)
);

CREATE TABLE health_outcomes (
    county_fips TEXT NOT NULL,
    data_year INTEGER NOT NULL,
    diabetes_pct REAL NOT NULL,
    obesity_pct REAL NOT NULL,
    hypertension_pct REAL NOT NULL,
    poor_or_fair_health_pct REAL NOT NULL,
    smoking_pct REAL NOT NULL,
    frequent_physical_distress_pct REAL NOT NULL,
    routine_checkup_pct REAL NOT NULL,
    preventable_hospital_stays_per_100k REAL NOT NULL,
    life_expectancy REAL NOT NULL,
    PRIMARY KEY (county_fips, data_year),
    FOREIGN KEY (county_fips) REFERENCES counties(county_fips)
);

CREATE TABLE provider_shortages (
    county_fips TEXT NOT NULL,
    data_year INTEGER NOT NULL,
    primary_care_physicians_per_100k REAL NOT NULL,
    mental_health_providers_per_100k REAL NOT NULL,
    dental_providers_per_100k REAL NOT NULL,
    hpsa_primary_care_score REAL NOT NULL,
    hpsa_primary_care_count INTEGER NOT NULL,
    hpsa_mental_health_score REAL NOT NULL,
    hpsa_mental_health_count INTEGER NOT NULL,
    hpsa_dental_score REAL NOT NULL,
    hpsa_dental_count INTEGER NOT NULL,
    provider_access_index REAL NOT NULL,
    PRIMARY KEY (county_fips, data_year),
    FOREIGN KEY (county_fips) REFERENCES counties(county_fips)
);

CREATE TABLE hospital_quality (
    county_fips TEXT NOT NULL,
    data_year INTEGER NOT NULL,
    hospital_count INTEGER NOT NULL,
    acute_care_hospitals INTEGER NOT NULL,
    emergency_services_count INTEGER NOT NULL,
    hospital_beds_per_1000 REAL NOT NULL,
    avg_hospital_star_rating REAL NOT NULL,
    readmission_rate_pct REAL NOT NULL,
    readmission_worse_measure_count REAL NOT NULL,
    PRIMARY KEY (county_fips, data_year),
    FOREIGN KEY (county_fips) REFERENCES counties(county_fips)
);

CREATE TABLE access_risk_scores (
    county_fips TEXT NOT NULL,
    data_year INTEGER NOT NULL,
    access_risk_score REAL NOT NULL,
    access_risk_tier TEXT NOT NULL,
    high_access_risk INTEGER NOT NULL CHECK (high_access_risk IN (0, 1)),
    socioeconomic_need_index REAL NOT NULL,
    insurance_access_burden_index REAL NOT NULL,
    provider_gap_index REAL NOT NULL,
    chronic_burden_index REAL NOT NULL,
    hospital_quality_gap_index REAL NOT NULL,
    top_risk_factor TEXT NOT NULL,
    PRIMARY KEY (county_fips, data_year),
    FOREIGN KEY (county_fips) REFERENCES counties(county_fips)
);

CREATE TABLE source_status (
    county_fips TEXT NOT NULL,
    data_year INTEGER NOT NULL,
    data_mode TEXT NOT NULL,
    source_acs TEXT NOT NULL,
    source_cdc_places TEXT NOT NULL,
    source_hrsa_hpsa TEXT NOT NULL,
    source_cms_hospital_quality TEXT NOT NULL,
    fallback_fields_note TEXT NOT NULL,
    PRIMARY KEY (county_fips, data_year),
    FOREIGN KEY (county_fips) REFERENCES counties(county_fips)
);

CREATE TABLE model_outputs (
    county_fips TEXT,
    county_name TEXT,
    target_mode TEXT,
    target TEXT,
    actual_target INTEGER,
    predicted_target INTEGER,
    predicted_target_probability REAL
);
