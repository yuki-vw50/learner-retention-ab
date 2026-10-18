-- 03_engagement_segments.sql
-- Retention by engagement band and variant.
-- The gate sits at level 30 (control) or 40 (treatment), so bands are cut around those levels.
-- CAUTION: sum_gamerounds is measured AFTER assignment (a post-treatment variable),
-- so these splits are descriptive only. The causal readout is 02 + the z-test in Python.

WITH banded AS (
    SELECT
        version,
        retention_7,
        CASE
            WHEN sum_gamerounds = 0   THEN '0. never played'
            WHEN sum_gamerounds < 30  THEN '1. 1-29 rounds'
            WHEN sum_gamerounds < 40  THEN '2. 30-39 rounds'
            WHEN sum_gamerounds < 100 THEN '3. 40-99 rounds'
            ELSE                           '4. 100+ rounds'
        END AS engagement_band
    FROM players
)
SELECT
    engagement_band,
    version,
    COUNT(*) AS n_players,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY version), 2) AS pct_of_variant,
    ROUND(AVG(CASE WHEN retention_7 THEN 1.0 ELSE 0 END), 4) AS d7_retention
FROM banded
GROUP BY engagement_band, version
ORDER BY engagement_band, version;
