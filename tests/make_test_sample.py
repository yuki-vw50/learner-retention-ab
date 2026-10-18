"""
Generate a SMALL FAKE dataset with the same columns as the Duolingo learning traces.

Purpose: testing only. It lets you check that the SQL and charts run end to end
before downloading the real 361 MB file. Numbers produced from this file are
meaningless and must never be reported.

Run: python tests/make_test_sample.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(0)
OUT = Path(__file__).resolve().parent / "fake_traces_sample.csv.gz"

COURSES = [("en", "es"), ("en", "fr"), ("en", "de"), ("es", "en"), ("en", "it"), ("pt", "en")]
WORDS = {
    "es": ["comer", "ser", "estar", "tener", "hablar", "agua", "libro", "nosotros", "porque", "mujer"],
    "fr": ["manger", "etre", "avoir", "parler", "eau", "livre", "nous", "parce", "femme", "chat"],
    "de": ["essen", "sein", "haben", "sprechen", "wasser", "buch", "wir", "weil", "frau", "katze"],
    "en": ["eat", "be", "have", "speak", "water", "book", "we", "because", "woman", "cat"],
    "it": ["mangiare", "essere", "avere", "parlare", "acqua", "libro", "noi", "perche", "donna", "gatto"],
}
START = 1362096000  # a fixed epoch start; 14-day window
rows = []
for user in range(1500):
    ui, learn = COURSES[rng.integers(len(COURSES))]
    engagement = rng.beta(1.2, 3)
    first_day = rng.integers(0, 14)
    seen = {}
    for day in range(first_day, 14):
        if day > first_day and rng.random() > engagement:
            continue
        for _ in range(rng.integers(1, 4)):
            ts = START + day * 86400 + int(rng.integers(0, 86400))
            for w in rng.choice(len(WORDS[learn]), size=rng.integers(3, 8), replace=False):
                word = WORDS[learn][w]
                last_ts, hs, hc = seen.get(word, (ts - int(rng.integers(3600, 86400 * 20)), 0, 0))
                delta = max(ts - last_ts, 60)
                p = np.clip(0.95 * np.exp(-delta / 86400 / (2 + hs)) + rng.normal(0, 0.05), 0, 1)
                s_seen = int(rng.integers(1, 4))
                s_corr = int(rng.binomial(s_seen, p))
                rows.append((s_corr / s_seen, ts, delta, f"u{user}", learn, ui,
                             f"{learn}_{w}", f"{word}/{word}<n>", hs, hc, s_seen, s_corr))
                seen[word] = (ts, hs + s_seen, hc + s_corr)

cols = ["p_recall", "timestamp", "delta", "user_id", "learning_language", "ui_language",
        "lexeme_id", "lexeme_string", "history_seen", "history_correct", "session_seen",
        "session_correct"]
pd.DataFrame(rows, columns=cols).to_csv(OUT, index=False)
print(f"Wrote {len(rows):,} FAKE rows to {OUT}")
