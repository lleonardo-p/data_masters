WITH metric_totals AS (
    SELECT
        SUM(notification_count) AS notifications,
        SUM(confirmed_case_count) AS confirmed,
        SUM(discarded_case_count) AS discarded,
        SUM(hospitalized_case_count) AS hospitalized,
        SUM(death_by_disease_count) AS deaths
    FROM "AwsDataCatalog"."baip_dev_gold"."dengue_fact_dengue_cases"
)
SELECT
    'metric_totals_are_sane' AS check_name,
    notifications > 0
        AND confirmed BETWEEN 0 AND notifications
        AND discarded BETWEEN 0 AND notifications
        AND hospitalized BETWEEN 0 AND notifications
        AND deaths BETWEEN 0 AND notifications AS passed,
    CONCAT(
        'notifications=', CAST(notifications AS VARCHAR),
        ', confirmed=', CAST(confirmed AS VARCHAR),
        ', discarded=', CAST(discarded AS VARCHAR),
        ', hospitalized=', CAST(hospitalized AS VARCHAR),
        ', deaths=', CAST(deaths AS VARCHAR)
    ) AS details
FROM metric_totals;
