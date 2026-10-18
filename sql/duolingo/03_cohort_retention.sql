-- 03_cohort_retention.sql
-- Cohort retention: of learners first seen on day D, what share came back on day D+N?
-- Only cohorts with a full 7 days of follow-up inside the data window are kept,
-- so later cohorts don't look artificially worse.

WITH first_seen AS (
    SELECT user_id, MIN(lesson_date) AS cohort_date
    FROM lessons
    GROUP BY user_id
),
activity AS (
    SELECT DISTINCT
        l.user_id,
        f.cohort_date,
        DATE_DIFF('day', f.cohort_date, l.lesson_date) AS day_n
    FROM lessons l
    JOIN first_seen f USING (user_id)
),
window_end AS (
    SELECT MAX(lesson_date) AS last_date FROM lessons
),
cohort_sizes AS (
    SELECT cohort_date, COUNT(*) AS cohort_size
    FROM first_seen
    GROUP BY cohort_date
)
SELECT
    a.cohort_date,
    c.cohort_size,
    a.day_n,
    COUNT(DISTINCT a.user_id)                                 AS active_users,
    ROUND(COUNT(DISTINCT a.user_id) * 1.0 / c.cohort_size, 4) AS retention_rate
FROM activity a
JOIN cohort_sizes c USING (cohort_date)
CROSS JOIN window_end w
WHERE a.day_n BETWEEN 0 AND 7
  AND a.cohort_date <= w.last_date - INTERVAL 7 DAY
GROUP BY a.cohort_date, c.cohort_size, a.day_n
ORDER BY a.cohort_date, a.day_n;
