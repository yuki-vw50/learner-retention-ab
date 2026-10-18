-- 08_language_pairs.sql
-- Recall by course (native/interface language -> language being learned).

SELECT
    ui_language || ' -> ' || learning_language        AS course,
    COUNT(DISTINCT user_id)                           AS learners,
    COUNT(*)                                          AS practices,
    ROUND(SUM(session_correct) * 1.0 / SUM(session_seen), 4) AS recall_rate
FROM traces
GROUP BY ui_language, learning_language
HAVING COUNT(DISTINCT user_id) >= 100
ORDER BY learners DESC;
