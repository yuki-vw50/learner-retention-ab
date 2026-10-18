-- 05_forgetting_curve.sql
-- How does recall drop as time since a word was last practiced grows?
-- Split by how many times the learner had already seen the word (practice depth).

WITH bucketed AS (
    SELECT
        CASE
            WHEN days_since_last_seen < 1.0/24 THEN 0
            WHEN days_since_last_seen < 1      THEN 1
            WHEN days_since_last_seen < 3      THEN 2
            WHEN days_since_last_seen < 7      THEN 3
            WHEN days_since_last_seen < 30     THEN 4
            ELSE 5
        END AS gap_order,
        CASE
            WHEN days_since_last_seen < 1.0/24 THEN '< 1 hour'
            WHEN days_since_last_seen < 1      THEN '1 hour - 1 day'
            WHEN days_since_last_seen < 3      THEN '1 - 3 days'
            WHEN days_since_last_seen < 7      THEN '3 - 7 days'
            WHEN days_since_last_seen < 30     THEN '1 - 4 weeks'
            ELSE '1 month +'
        END AS time_since_last_practice,
        CASE
            WHEN history_seen <= 2  THEN 'a. seen 1-2 times'
            WHEN history_seen <= 10 THEN 'b. seen 3-10 times'
            ELSE                         'c. seen 11+ times'
        END AS practice_depth,
        session_seen,
        session_correct
    FROM traces
)
SELECT
    gap_order,
    time_since_last_practice,
    practice_depth,
    COUNT(*)                                          AS n_observations,
    ROUND(SUM(session_correct) * 1.0 / SUM(session_seen), 4) AS recall_rate
FROM bucketed
GROUP BY gap_order, time_since_last_practice, practice_depth
ORDER BY practice_depth, gap_order;
