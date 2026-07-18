SELECT
    notification_year,
    notification_month,
    classification_code,
    classification_name,
    confirmation_criterion_name,
    SUM(notification_count) AS notifications,
    SUM(confirmed_case_count) AS confirmed_cases,
    SUM(discarded_case_count) AS discarded_cases,
    SUM(alarm_case_count) AS alarm_cases,
    SUM(severe_case_count) AS severe_cases,
    SUM(under_investigation_count) AS under_investigation,
    SUM(death_by_disease_count) AS deaths
FROM "AwsDataCatalog"."baip_dev_gold"."vw_dengue_monthly_classification"
GROUP BY
    notification_year,
    notification_month,
    classification_code,
    classification_name,
    confirmation_criterion_name
ORDER BY
    notification_year,
    notification_month,
    notifications DESC;
