-- 01_data_quality.sql
-- Size, coverage, and validity checks before analysis.

SELECT
    COUNT(*)                                        AS n_rows,
    COUNT(DISTINCT user_id)                         AS n_users,
    COUNT(DISTINCT lexeme_id)                       AS n_words,
    (SELECT COUNT(*) FROM lessons)                  AS n_lessons,
    COUNT(DISTINCT learning_language)               AS n_learning_languages,
    MIN(lesson_date)                                AS first_date,
    MAX(lesson_date)                                AS last_date,
    SUM(CASE WHEN session_correct > session_seen THEN 1 ELSE 0 END) AS invalid_correct_counts,
    SUM(CASE WHEN p_recall < 0 OR p_recall > 1 THEN 1 ELSE 0 END)   AS invalid_recall_values
FROM traces;
