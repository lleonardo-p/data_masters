WITH measure_stats AS (
    SELECT
        COUNT(*) AS row_count,
        COUNT_IF(
            notification_count IS NULL
            OR notification_count <> 1
            OR NOT COALESCE(confirmed_case_count IN (0, 1), FALSE)
            OR NOT COALESCE(discarded_case_count IN (0, 1), FALSE)
            OR NOT COALESCE(alarm_case_count IN (0, 1), FALSE)
            OR NOT COALESCE(severe_case_count IN (0, 1), FALSE)
            OR NOT COALESCE(under_investigation_count IN (0, 1), FALSE)
            OR NOT COALESCE(hospitalized_case_count IN (0, 1), FALSE)
            OR NOT COALESCE(death_by_disease_count IN (0, 1), FALSE)
            OR NOT COALESCE(death_other_cause_count IN (0, 1), FALSE)
            OR NOT COALESCE(autochthonous_case_count IN (0, 1), FALSE)
            OR NOT COALESCE(quality_warning_count IN (0, 1), FALSE)
        ) AS invalid_measure_row_count
    FROM "AwsDataCatalog"."baip_dev_gold"."dengue_fact_dengue_cases"
)
SELECT
    'fact_measures_are_binary' AS check_name,
    invalid_measure_row_count = 0 AS passed,
    CONCAT(
        'row_count=',
        CAST(row_count AS VARCHAR),
        ', invalid_measure_row_count=',
        CAST(invalid_measure_row_count AS VARCHAR)
    ) AS details
FROM measure_stats;
