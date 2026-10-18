-- 07_engagement_segments.sql
-- Split learners into quartiles by number of active days (NTILE window function),
-- then compare their lesson volume and accuracy.

WITH per_user AS (
    SELECT
        user_id,
        COUNT(DISTINCT lesson_date)       AS active_days,
        COUNT(*)                          AS lessons,
        AVG(lesson_accuracy)              AS avg_accuracy
    FROM lessons
    GROUP BY user_id
),
segmented AS (
    SELECT *,
           NTILE(4) OVER (ORDER BY active_days, lessons) AS engagement_quartile
    FROM per_user
)
SELECT
    engagement_quartile,
    COUNT(*)                         AS learners,
    MIN(active_days)                 AS min_active_days,
    MAX(active_days)                 AS max_active_days,
    ROUND(AVG(lessons), 1)           AS avg_lessons,
    ROUND(AVG(avg_accuracy), 4)      AS avg_lesson_accuracy,
    ROUND(SUM(lessons) * 1.0 / (SELECT COUNT(*) FROM lessons), 4) AS share_of_all_lessons
FROM segmented
GROUP BY engagement_quartile
ORDER BY engagement_quartile;
