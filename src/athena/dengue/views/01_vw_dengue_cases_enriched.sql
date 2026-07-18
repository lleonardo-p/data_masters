CREATE OR REPLACE VIEW "baip_dev_gold"."vw_dengue_cases_enriched" AS
SELECT
    fact.case_id,
    fact.environment,
    disease.disease_code,
    disease.disease_name,
    notification_date.calendar_date AS notification_date,
    fact.notification_year,
    fact.notification_month,
    fact.notification_epidemiological_week,
    location.municipality_code_sinan AS residence_municipality_code_sinan,
    location.municipality_code_ibge AS residence_municipality_code_ibge,
    location.municipality_name AS residence_municipality_name,
    location.uf_code AS residence_uf_code,
    location.uf_abbreviation AS residence_uf_abbreviation,
    location.uf_name AS residence_uf_name,
    location.region_code AS residence_region_code,
    location.region_abbreviation AS residence_region_abbreviation,
    location.region_name AS residence_region_name,
    demographic.age_unit_code,
    demographic.age_unit_name,
    demographic.age_value,
    demographic.age_years,
    demographic.age_group_name,
    demographic.sex_code,
    demographic.sex_name,
    demographic.pregnancy_code,
    demographic.pregnancy_name,
    demographic.race_code,
    demographic.race_name,
    demographic.education_code,
    demographic.education_name,
    clinical.classification_code,
    clinical.classification_name,
    clinical.confirmation_criterion_code,
    clinical.confirmation_criterion_name,
    clinical.case_outcome_code,
    clinical.case_outcome_name,
    clinical.hospitalization_code,
    clinical.hospitalization_name,
    clinical.autochthonous_code,
    clinical.autochthonous_name,
    clinical.serotype_code,
    fact.notification_count,
    fact.confirmed_case_count,
    fact.discarded_case_count,
    fact.alarm_case_count,
    fact.severe_case_count,
    fact.under_investigation_count,
    fact.hospitalized_case_count,
    fact.death_by_disease_count,
    fact.death_other_cause_count,
    fact.autochthonous_case_count,
    fact.quality_warning_count,
    fact.data_quality_status,
    fact.quality_warning_codes,
    fact.gold_loaded_at
FROM "AwsDataCatalog"."baip_dev_gold"."dengue_fact_dengue_cases" AS fact
INNER JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_date" AS notification_date
    ON fact.notification_date_key = notification_date.date_key
INNER JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_location" AS location
    ON fact.residence_location_key = location.location_key
INNER JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_disease" AS disease
    ON fact.disease_key = disease.disease_key
INNER JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_demographic" AS demographic
    ON fact.demographic_key = demographic.demographic_key
INNER JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_clinical" AS clinical
    ON fact.clinical_key = clinical.clinical_key;
