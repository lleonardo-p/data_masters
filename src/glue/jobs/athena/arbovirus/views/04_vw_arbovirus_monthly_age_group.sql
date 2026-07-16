CREATE OR REPLACE VIEW "baip_dev_gold"."vw_arbovirus_monthly_age_group" AS
SELECT
    notification_year,
    notification_month,
    disease_code,
    disease_name,
    age_group_name,
    SUM(notification_count) AS notification_count,
    SUM(confirmed_case_count) AS confirmed_case_count,
    SUM(discarded_case_count) AS discarded_case_count,
    SUM(alarm_case_count) AS alarm_case_count,
    SUM(severe_case_count) AS severe_case_count,
    SUM(under_investigation_count) AS under_investigation_count,
    SUM(hospitalized_case_count) AS hospitalized_case_count,
    SUM(death_by_disease_count) AS death_by_disease_count,
    SUM(death_other_cause_count) AS death_other_cause_count,
    SUM(quality_warning_count) AS quality_warning_count
FROM "AwsDataCatalog"."baip_dev_gold"."vw_arbovirus_cases_enriched"
GROUP BY
    notification_year,
    notification_month,
    disease_code,
    disease_name,
    age_group_name;
