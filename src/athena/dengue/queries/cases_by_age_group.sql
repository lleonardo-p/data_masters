SELECT
    notification_year,
    notification_month,
    age_group_name,
    SUM(notification_count) AS notifications,
    SUM(confirmed_case_count) AS confirmed_cases,
    SUM(hospitalized_case_count) AS hospitalized_cases,
    SUM(death_by_disease_count) AS deaths,
    ROUND(
        100.0 * SUM(hospitalized_case_count)
        / NULLIF(SUM(confirmed_case_count), 0),
        2
    ) AS hospitalization_percentage_among_confirmed
FROM "AwsDataCatalog"."baip_dev_gold"."vw_dengue_monthly_age_group"
GROUP BY
    notification_year,
    notification_month,
    age_group_name
ORDER BY
    notification_year,
    notification_month,
    confirmed_cases DESC;
