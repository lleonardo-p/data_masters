SELECT
    notification_year,
    notification_month,
    SUM(notification_count) AS notifications,
    SUM(confirmed_case_count) AS confirmed_cases,
    SUM(discarded_case_count) AS discarded_cases,
    SUM(alarm_case_count) AS alarm_cases,
    SUM(severe_case_count) AS severe_cases,
    SUM(hospitalized_case_count) AS hospitalized_cases,
    SUM(death_by_disease_count) AS deaths
FROM "AwsDataCatalog"."baip_dev_gold"."dengue_fact_dengue_cases"
GROUP BY
    notification_year,
    notification_month
ORDER BY
    notification_year,
    notification_month;
