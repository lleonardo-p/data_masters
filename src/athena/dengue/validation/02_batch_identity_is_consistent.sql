WITH batch_stats AS (
    SELECT
        COUNT(*) AS row_count,
        COUNT_IF(source_batch_id IS NULL) AS missing_batch_id_count,
        COUNT(DISTINCT source_batch_id) AS distinct_batch_id_count
    FROM "AwsDataCatalog"."baip_dev_gold"."dengue_fact_dengue_cases"
)
SELECT
    'batch_identity_is_consistent' AS check_name,
     missing_batch_id_count = 0
        AND distinct_batch_id_count >= 1 AS passed,
    CONCAT(
        'row_count=',
        CAST(row_count AS VARCHAR),
        ', missing_batch_id_count=',
        CAST(missing_batch_id_count AS VARCHAR),
        ', distinct_batch_id_count=',
        CAST(distinct_batch_id_count AS VARCHAR)
    ) AS details
FROM batch_stats;
