SELECT
    notification_year,
    notification_month,
    municipality_code_ibge,
    municipality_name,
    uf_abbreviation,
    SUM(notification_count) AS notifications,
    SUM(confirmed_case_count) AS confirmed_cases,
    SUM(hospitalized_case_count) AS hospitalized_cases,
    SUM(death_by_disease_count) AS deaths,
    ROUND(
        100.0 * SUM(confirmed_case_count)
        / NULLIF(SUM(notification_count), 0),
        2
    ) AS confirmation_percentage
FROM "AwsDataCatalog"."baip_dev_gold"."vw_arbovirus_monthly_municipality"
GROUP BY
    notification_year,
    notification_month,
    municipality_code_ibge,
    municipality_name,
    uf_abbreviation
ORDER BY
    confirmed_cases DESC,
    notifications DESC
LIMIT 100;
