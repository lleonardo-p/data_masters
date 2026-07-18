WITH orphan_counts AS (
    SELECT
        COUNT_IF(disease.disease_key IS NULL) AS disease_orphans,
        COUNT_IF(demographic.demographic_key IS NULL) AS demographic_orphans,
        COUNT_IF(clinical.clinical_key IS NULL) AS clinical_orphans,
        COUNT_IF(notification_date.date_key IS NULL) AS date_orphans,
        COUNT_IF(residence.location_key IS NULL) AS residence_orphans
    FROM "AwsDataCatalog"."baip_dev_gold"."dengue_fact_dengue_cases" AS fact
    LEFT JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_disease" AS disease
        ON fact.disease_key = disease.disease_key
    LEFT JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_demographic" AS demographic
        ON fact.demographic_key = demographic.demographic_key
    LEFT JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_clinical" AS clinical
        ON fact.clinical_key = clinical.clinical_key
    LEFT JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_date" AS notification_date
        ON fact.notification_date_key = notification_date.date_key
    LEFT JOIN "AwsDataCatalog"."baip_dev_gold"."dengue_dim_location" AS residence
        ON fact.residence_location_key = residence.location_key
)
SELECT
    'core_dimension_keys_are_valid' AS check_name,
    disease_orphans = 0
        AND demographic_orphans = 0
        AND clinical_orphans = 0
        AND date_orphans = 0
        AND residence_orphans = 0 AS passed,
    CONCAT(
        'disease=', CAST(disease_orphans AS VARCHAR),
        ', demographic=', CAST(demographic_orphans AS VARCHAR),
        ', clinical=', CAST(clinical_orphans AS VARCHAR),
        ', date=', CAST(date_orphans AS VARCHAR),
        ', residence=', CAST(residence_orphans AS VARCHAR)
    ) AS details
FROM orphan_counts;
