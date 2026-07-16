SELECT
    notification_year,
    notification_month,
    uf_abbreviation,
    uf_name,
    region_name,
    SUM(notification_count) AS notifications,
    SUM(confirmed_case_count) AS confirmed_cases,
    SUM(alarm_case_count) AS alarm_cases,
    SUM(severe_case_count) AS severe_cases,
    SUM(hospitalized_case_count) AS hospitalized_cases,
    SUM(death_by_disease_count) AS deaths
FROM "AwsDataCatalog"."baip_dev_gold"."vw_arbovirus_monthly_uf"
GROUP BY
    notification_year,
    notification_month,
    uf_abbreviation,
    uf_name,
    region_name
ORDER BY
    notification_year,
    notification_month,
    confirmed_cases DESC;
