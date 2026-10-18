-- 01_quality_checks.sql
-- Sanity checks before any statistics: duplicates, nulls, group sizes, outliers.
-- Table: players(userid, version, sum_gamerounds, retention_1, retention_7)

SELECT
    COUNT(*)                                   AS n_rows,
    COUNT(DISTINCT userid)                     AS n_users,
    COUNT(*) - COUNT(DISTINCT userid)          AS duplicate_rows,
    SUM(CASE WHEN version IS NULL THEN 1 ELSE 0 END)        AS null_version,
    SUM(CASE WHEN sum_gamerounds IS NULL THEN 1 ELSE 0 END) AS null_rounds,
    SUM(CASE WHEN sum_gamerounds = 0 THEN 1 ELSE 0 END)     AS never_played,
    MAX(sum_gamerounds)                        AS max_rounds,
    QUANTILE_CONT(sum_gamerounds, 0.99)        AS p99_rounds
FROM players;
