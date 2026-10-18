-- 06_hardest_words.sql
-- Top 10 hardest root words per language course, by recall rate.
-- Words need enough practice volume to be ranked reliably.

WITH word_stats AS (
    SELECT
        learning_language,
        lemma,
        COUNT(*)                                          AS n_practices,
        COUNT(DISTINCT user_id)                           AS n_learners,
        SUM(session_correct) * 1.0 / SUM(session_seen)    AS recall_rate
    FROM traces
    WHERE lemma <> ''
    GROUP BY learning_language, lemma
    HAVING COUNT(DISTINCT user_id) >= 50
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY learning_language ORDER BY recall_rate ASC) AS difficulty_rank,
        AVG(recall_rate) OVER (PARTITION BY learning_language)                       AS course_avg_recall
    FROM word_stats
)
SELECT
    learning_language,
    difficulty_rank,
    lemma,
    n_learners,
    ROUND(recall_rate, 4)                     AS recall_rate,
    ROUND(recall_rate - course_avg_recall, 4) AS vs_course_avg
FROM ranked
WHERE difficulty_rank <= 10
ORDER BY learning_language, difficulty_rank;
