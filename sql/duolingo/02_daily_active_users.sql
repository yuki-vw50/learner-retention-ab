-- 02_daily_active_users.sql
-- Daily active learners and lessons, with a 7-day rolling average (window function).

WITH daily AS (
    SELECT
        lesson_date,
        COUNT(DISTINCT user_id) AS dau,
        COUNT(*)                AS lessons
    FROM lessons
    GROUP BY lesson_date
)
SELECT
    lesson_date,
    dau,
    lessons,
    ROUND(lessons * 1.0 / dau, 2) AS lessons_per_active_user,
    ROUND(AVG(dau) OVER (ORDER BY lesson_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0)
        AS dau_7day_avg
FROM daily
ORDER BY lesson_date;
