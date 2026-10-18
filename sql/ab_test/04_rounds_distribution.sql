-- 04_rounds_distribution.sql
-- Share of each variant's players who reached at least N rounds (a survival curve).
-- Uses a window function to accumulate from the top of the distribution down.

WITH counts AS (
    SELECT version, LEAST(sum_gamerounds, 100) AS rounds, COUNT(*) AS n
    FROM players
    GROUP BY 1, 2
),
cum AS (
    SELECT
        version,
        rounds,
        SUM(n) OVER (PARTITION BY version ORDER BY rounds DESC
                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS n_at_least,
        SUM(n) OVER (PARTITION BY version) AS n_total
    FROM counts
)
SELECT version, rounds, ROUND(n_at_least * 1.0 / n_total, 4) AS share_reaching
FROM cum
ORDER BY version, rounds;
