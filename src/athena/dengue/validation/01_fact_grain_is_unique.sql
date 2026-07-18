WITH fact_stats AS (
    SELECT
        COUNT(*) AS row_count,
        COUNT(DISTINCT case_id) AS distinct_case_count
    FROM "AwsDataCatalog"."baip_dev_gold"."dengue_fact_dengue_cases"
)
SELECT
    'fact_grain_is_unique' AS check_name,
    row_count = distinct_case_count AS passed,
    CONCAT(
        'row_count=',
        CAST(row_count AS VARCHAR),
        ', distinct_case_count=',
        CAST(distinct_case_count AS VARCHAR)
    ) AS details
FROM fact_stats;
