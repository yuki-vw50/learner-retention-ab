-- 02_metrics_by_group.sql
-- Core experiment readout: sample size and retention rate per variant.
-- Outlier users (above the 99.99th percentile of rounds) are flagged, not silently dropped.

WITH thresholds AS (
    SELECT QUANTILE_CONT(sum_gamerounds, 0.9999) AS outlier_cutoff
    FROM players
)
SELECT
    p.version,
    COUNT(*)                                                AS n_players,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)      AS pct_of_traffic,
    SUM(CASE WHEN p.retention_1 THEN 1 ELSE 0 END)          AS retained_d1,
    SUM(CASE WHEN p.retention_7 THEN 1 ELSE 0 END)          AS retained_d7,
    ROUND(AVG(CASE WHEN p.retention_1 THEN 1.0 ELSE 0 END), 4) AS d1_retention,
    ROUND(AVG(CASE WHEN p.retention_7 THEN 1.0 ELSE 0 END), 4) AS d7_retention,
    MEDIAN(p.sum_gamerounds)                                AS median_rounds,
    SUM(CASE WHEN p.sum_gamerounds > t.outlier_cutoff THEN 1 ELSE 0 END) AS outlier_players
FROM players p
CROSS JOIN thresholds t
GROUP BY p.version
ORDER BY p.version;
