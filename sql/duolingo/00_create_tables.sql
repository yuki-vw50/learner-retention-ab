-- 00_create_tables.sql
-- Build a clean table from the raw learning traces.
-- One raw row = one word (lexeme) practiced by one user in one lesson.
-- {DATA_PATH} is filled in by src/duolingo_analysis.py.

CREATE OR REPLACE TABLE traces AS
SELECT
    user_id,
    learning_language,
    ui_language,
    lexeme_id,
    SPLIT_PART(SPLIT_PART(lexeme_string, '/', 2), '<', 1)  AS lemma,       -- root word, e.g. "comer"
    lexeme_string,
    TO_TIMESTAMP(timestamp)                                AS lesson_ts,
    CAST(TO_TIMESTAMP(timestamp) AS DATE)                  AS lesson_date,
    timestamp                                              AS lesson_epoch,
    delta / 86400.0                                        AS days_since_last_seen,
    history_seen,
    history_correct,
    session_seen,
    session_correct,
    p_recall
FROM read_csv_auto('{DATA_PATH}')
WHERE session_seen > 0;

-- A "lesson" = one user at one timestamp (all words practiced together).
CREATE OR REPLACE TABLE lessons AS
SELECT
    user_id,
    learning_language,
    lesson_ts,
    lesson_date,
    COUNT(*)                                   AS words_practiced,
    SUM(session_correct) * 1.0 / SUM(session_seen) AS lesson_accuracy
FROM traces
GROUP BY user_id, learning_language, lesson_ts, lesson_date;
