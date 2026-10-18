-- 04_retention_by_language.sql
-- Day-1 and Day-7 "came back" rates by language course (learners with full follow-up).
-- "Retained on day N" = active exactly on day N after first appearing,
-- the same definition used in the cohort table.

WITH first_seen AS (
    SELECT user_id,
           ARG_MIN(learning_language, lesson_ts) AS first_course,
           MIN(lesson_date)                      AS cohort_date
    FROM lessons
    GROUP BY user_id
),
eligible AS (
    SELECT f.*
    FROM first_seen f
    WHERE f.cohort_date <= (SELECT MAX(lesson_date) FROM lessons) - INTERVAL 7 DAY
),
flags AS (
    SELECT
        e.user_id,
        e.first_course,
        MAX(CASE WHEN DATE_DIFF('day', e.cohort_date, l.lesson_date) = 1 THEN 1 ELSE 0 END) AS active_d1,
        MAX(CASE WHEN DATE_DIFF('day', e.cohort_date, l.lesson_date) = 7 THEN 1 ELSE 0 END) AS active_d7,
        COUNT(DISTINCT l.lesson_date) AS active_days_total
    FROM eligible e
    JOIN lessons l USING (user_id)
    GROUP BY e.user_id, e.first_course
)
SELECT
    first_course                         AS learning_language,
    COUNT(*)                             AS learners,
    ROUND(AVG(active_d1), 4)             AS d1_retention,
    ROUND(AVG(active_d7), 4)             AS d7_retention,
    ROUND(AVG(active_days_total), 2)     AS avg_active_days,
    RANK() OVER (ORDER BY AVG(active_d7) DESC) AS d7_rank
FROM flags
GROUP BY first_course
HAVING COUNT(*) >= 100
ORDER BY d7_rank;
