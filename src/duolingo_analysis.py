"""
Learner retention and forgetting analysis on Duolingo's public learning-trace data
(Settles & Meeder, 2016: ~13 million practice records).

Run on the real data (after downloading it, see README):
    python src/duolingo_analysis.py --data data/raw/settles.acl16.learning_traces.13m.csv.gz

Test the pipeline on fake data first (optional):
    python tests/make_test_sample.py
    python src/duolingo_analysis.py --data tests/fake_traces_sample.csv.gz --test

Outputs: outputs/duolingo_results.md, outputs/figures/duo_*.png, outputs/tableau/duo_*.csv
(--test writes to outputs/_TEST_ONLY/ instead so fake numbers never mix with real ones.)
"""
import argparse
import time
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql" / "duolingo"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, RULE = "#0b0b0b", "#52514e", "#c3c2b7"
LANG = {"en": "English", "es": "Spanish", "fr": "French", "de": "German",
        "it": "Italian", "pt": "Portuguese"}


def style(ax, title, ylabel=None, xlabel=None):
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=INK)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK2)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(RULE)
    ax.tick_params(colors=INK2)
    ax.grid(axis="y", color="#e8e7e3", linewidth=0.8)
    ax.set_axisbelow(True)


def pct(ax):
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "raw" / "settles.acl16.learning_traces.13m.csv.gz"))
    ap.add_argument("--test", action="store_true", help="fake-data test run")
    args = ap.parse_args()

    data = Path(args.data).resolve()
    if not data.exists():
        raise SystemExit(f"Data file not found: {data}\nSee README for the download link.")

    out = ROOT / "outputs" / ("_TEST_ONLY" if args.test else "")
    fig_dir, tab_dir = out / "figures", out / "tableau"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    t0 = time.time()
    print("Loading data (the full file takes a minute or two)...")
    con.sql((SQL / "00_create_tables.sql").read_text().replace("{DATA_PATH}", data.as_posix()))

    results = {}
    for f in sorted(SQL.glob("0[1-8]_*.sql")):
        df = con.sql(f.read_text()).df()
        results[f.stem] = df
        df.to_csv(tab_dir / f"duo_{f.stem[3:]}.csv", index=False)
        print(f"  ran {f.name:<32} -> {len(df):>4} rows")

    q = results["01_data_quality"].iloc[0]
    dau = results["02_daily_active_users"]
    cohort = results["03_cohort_retention"]
    by_lang = results["04_retention_by_language"]
    forget = results["05_forgetting_curve"]
    hard = results["06_hardest_words"]
    seg = results["07_engagement_segments"]
    pairs = results["08_language_pairs"]

    # Average retention curve across cohorts, weighted by cohort size
    cohort["weighted"] = cohort.active_users
    curve = cohort.groupby("day_n").agg(active=("active_users", "sum"),
                                        size=("cohort_size", "sum"))
    curve["rate"] = curve.active / curve["size"]
    curve.reset_index().to_csv(tab_dir / "duo_retention_curve.csv", index=False)

    # ---------- Figures ----------
    # 1. Retention curve
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(curve.index, curve.rate, color=BLUE, linewidth=2, marker="o", markersize=6)
    for d in (1, 7):
        if d in curve.index:
            ax.annotate(f"Day {d}: {curve.rate[d]:.1%}", (d, curve.rate[d]),
                        textcoords="offset points", xytext=(8, 10), color=INK, fontsize=10)
    ax.set_ylim(0, 1.05)
    pct(ax)
    style(ax, "Share of learners active N days after first appearing",
          "Learners active that day", "Days since first appearing in the data")
    fig.tight_layout()
    fig.savefig(fig_dir / "duo_retention_curve.png", dpi=160, facecolor="#fcfcfb")
    plt.close(fig)

    # 2. Cohort heatmap (sequential single-hue)
    pivot = cohort.pivot(index="cohort_date", columns="day_n", values="retention_rate")
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(pivot) + 1.5))
    im = ax.imshow(pivot.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(pivot.shape[1]), [f"D{c}" for c in pivot.columns])
    ax.set_yticks(range(pivot.shape[0]), [str(d)[:10] for d in pivot.index])
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=8,
                        color="white" if v > 0.55 else INK)
    ax.set_title("Cohort retention by first-active date", loc="left", fontsize=12,
                 fontweight="bold", color=INK)
    ax.tick_params(colors=INK2, length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    fig.savefig(fig_dir / "duo_cohort_heatmap.png", dpi=160, facecolor="#fcfcfb")
    plt.close(fig)

    # 3. Forgetting curve by practice depth
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels = forget.drop_duplicates("gap_order").sort_values("gap_order")
    for depth, color in zip(sorted(forget.practice_depth.unique()), [ORANGE, BLUE, AQUA]):
        s = forget[forget.practice_depth == depth].sort_values("gap_order")
        ax.plot(s.gap_order, s.recall_rate, color=color, linewidth=2, marker="o",
                markersize=6, label=depth[3:])
    ax.set_xticks(labels.gap_order, labels.time_since_last_practice, rotation=0, fontsize=9)
    pct(ax)
    style(ax, "Recall drops the longer a word goes unpracticed",
          "Answers correct", "Time since the word was last practiced")
    ax.legend(title="Word previously", frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / "duo_forgetting_curve.png", dpi=160, facecolor="#fcfcfb")
    plt.close(fig)

    # 4. Day-7 retention by course
    fig, ax = plt.subplots(figsize=(8, 0.5 * len(by_lang) + 1.2))
    s = by_lang.sort_values("d7_retention")
    names = [LANG.get(x, x) for x in s.learning_language]
    ax.barh(names, s.d7_retention, color=BLUE, height=0.6, edgecolor="#fcfcfb", linewidth=2)
    for y, (v, n) in enumerate(zip(s.d7_retention, s.learners)):
        ax.text(v + 0.003, y, f"{v:.1%}  (n={n:,})", va="center", fontsize=9, color=INK)
    ax.set_xlim(0, s.d7_retention.max() * 1.35)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
    style(ax, "Day-7 retention by language being learned")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color="#e8e7e3", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(fig_dir / "duo_retention_by_language.png", dpi=160, facecolor="#fcfcfb")
    plt.close(fig)

    # ---------- Key numbers for the write-up ----------
    d1 = curve.rate.get(1, np.nan)
    d7 = curve.rate.get(7, np.nan)
    f_first = forget[(forget.practice_depth.str.startswith("a")) & (forget.gap_order == 1)]
    f_late = forget[(forget.practice_depth.str.startswith("a")) & (forget.gap_order == 4)]
    deep_late = forget[(forget.practice_depth.str.startswith("c")) & (forget.gap_order == 4)]
    top_q, bottom_q = seg.iloc[-1], seg.iloc[0]
    best, worst = by_lang.iloc[0], by_lang.iloc[-1]

    def val(df, col="recall_rate"):
        return df[col].iloc[0] if len(df) else float("nan")

    warning = ("\n> **TEST RUN ON FAKE DATA. These numbers are meaningless. Do not report them.**\n"
               if args.test else "")
    md = f"""# Duolingo Learner Retention & Forgetting: Results
{warning}
*Generated by `src/duolingo_analysis.py` in {time.time() - t0:.0f}s. Every number is computed from the data.*

## Data
- {int(q.n_rows):,} practice records, {int(q.n_users):,} learners, {int(q.n_lessons):,} lessons,
  {int(q.n_words):,} distinct words, {int(q.n_learning_languages)} languages being learned.
- Window: {str(q.first_date)[:10]} to {str(q.last_date)[:10]}.
- Validity checks: {int(q.invalid_correct_counts)} rows with more correct answers than attempts,
  {int(q.invalid_recall_values)} recall values outside 0-1.

## Key findings
1. **Retention:** {d1:.1%} of learners were active again the day after they first appeared,
   and {d7:.1%} were active on day 7 (cohorts with a full week of follow-up).
2. **By course:** Day-7 retention ranged from {best.d7_retention:.1%} ({LANG.get(best.learning_language, best.learning_language)})
   to {worst.d7_retention:.1%} ({LANG.get(worst.learning_language, worst.learning_language)}).
3. **Forgetting:** for words seen only 1-2 times before, recall was {val(f_first):.1%} when practiced again
   within a day vs. {val(f_late):.1%} after 1-4 weeks. Words seen 11+ times held {val(deep_late):.1%} recall
   after 1-4 weeks. {"Repeated practice slows forgetting, which is the idea behind spaced repetition." if val(deep_late) > val(f_late) else "Check this result: well-practiced words did not hold up better here."}
4. **Engagement concentration:** the most engaged quarter of learners
   (active {int(top_q.min_active_days)}-{int(top_q.max_active_days)} days) completed {top_q.share_of_all_lessons:.0%} of all lessons;
   the least engaged quarter completed {bottom_q.share_of_all_lessons:.0%}.

## Retention by course
{by_lang.to_markdown(index=False)}

## Forgetting curve
{forget.to_markdown(index=False)}

## Engagement quartiles
{seg.to_markdown(index=False)}

## Recall by course (interface -> learning language)
{pairs.to_markdown(index=False)}

## Hardest words (first 3 per course)
{hard[hard.difficulty_rank <= 3].to_markdown(index=False)}

## Caveats
- "First appeared" means first seen in this two-week sample, not necessarily the sign-up date,
  so retention here describes returning activity rather than true new-user retention.
- The data is from 2013 and is a research sample, so it may not reflect today's product.

## Suggested resume bullet (numbers filled in from this run)
> Analyzed {int(q.n_rows / 1e6)}M+ Duolingo learning records ({int(q.n_users):,} learners) in SQL (CTEs, window functions)
> to build cohort retention curves (Day-1 {d1:.0%}, Day-7 {d7:.0%}) and a forgetting curve showing recall falls
> from {val(f_first):.0%} to {val(f_late):.0%} without review; paired with an A/B test analysis of 90K players.
"""
    (out / "duolingo_results.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
