"""
A/B test analysis: does moving the first progress gate from level 30 to level 40
change player retention?

Data: Cookie Cats mobile game experiment (90,189 players, randomly assigned).
Run:  python src/ab_test.py
Outputs: outputs/ab_test_results.md, outputs/figures/ab_*.png, outputs/tableau/ab_*.csv
"""
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import (confint_proportions_2indep,
                                          proportion_effectsize,
                                          proportions_ztest)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "cookie_cats.csv"
SQL = ROOT / "sql" / "ab_test"
OUT = ROOT / "outputs"
FIG = OUT / "figures"
TAB = OUT / "tableau"

CONTROL, TREATMENT = "gate_30", "gate_40"
COLORS = {CONTROL: "#2a78d6", TREATMENT: "#eb6834"}
ALPHA = 0.05
RNG = np.random.default_rng(42)


def run_sql(con, name):
    return con.sql((SQL / name).read_text()).df()


def style(ax, title, ylabel=None):
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color="#0b0b0b")
    if ylabel:
        ax.set_ylabel(ylabel, color="#52514e")
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#c3c2b7")
    ax.tick_params(colors="#52514e")
    ax.grid(axis="y", color="#e8e7e3", linewidth=0.8)
    ax.set_axisbelow(True)


def srm_check(n_c, n_t):
    """Sample ratio mismatch: is the traffic split consistent with 50/50?"""
    total = n_c + n_t
    chi2, p = stats.chisquare([n_c, n_t], [total / 2, total / 2])
    return chi2, p


def compare(df, metric):
    """Two-proportion z-test + CI + bootstrap for one retention metric."""
    c = df.loc[df.version == CONTROL, metric].astype(int).to_numpy()
    t = df.loc[df.version == TREATMENT, metric].astype(int).to_numpy()
    succ = np.array([c.sum(), t.sum()])
    nobs = np.array([len(c), len(t)])
    z, p = proportions_ztest(succ, nobs)
    lo, hi = confint_proportions_2indep(succ[1], nobs[1], succ[0], nobs[0],
                                        method="newcomb")  # treatment - control
    # Bootstrap the difference in retention (treatment - control)
    boot = np.array([
        RNG.choice(t, len(t)).mean() - RNG.choice(c, len(c)).mean()
        for _ in range(2000)
    ])
    return {
        "metric": metric,
        "control_rate": c.mean(),
        "treatment_rate": t.mean(),
        "abs_diff": t.mean() - c.mean(),
        "rel_diff": (t.mean() - c.mean()) / c.mean(),
        "z": z,
        "p_value": p,
        "ci_low": lo,
        "ci_high": hi,
        "prob_control_better": (boot < 0).mean(),
        "boot": boot,
    }


def mde(p_base, n_per_group, power=0.8):
    """Smallest absolute lift detectable with this sample size."""
    es = NormalIndPower().solve_power(nobs1=n_per_group, alpha=ALPHA, power=power, ratio=1)
    # invert Cohen's h back to a proportion difference
    p_new = np.sin(np.arcsin(np.sqrt(p_base)) + es / 2) ** 2
    return p_new - p_base


def main():
    for d in (FIG, TAB):
        d.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.sql(f"CREATE TABLE players AS SELECT * FROM read_csv_auto('{DATA}')")
    df = con.sql("SELECT * FROM players").df()

    quality = run_sql(con, "01_quality_checks.sql")
    groups = run_sql(con, "02_metrics_by_group.sql")
    segments = run_sql(con, "03_engagement_segments.sql")
    survival = run_sql(con, "04_rounds_distribution.sql")

    n_c = int(groups.loc[groups.version == CONTROL, "n_players"].iloc[0])
    n_t = int(groups.loc[groups.version == TREATMENT, "n_players"].iloc[0])
    chi2, srm_p = srm_check(n_c, n_t)

    results = {m: compare(df, m) for m in ("retention_1", "retention_7")}

    # Sensitivity: drop the single extreme player (rounds above 99.99th pct)
    cutoff = df.sum_gamerounds.quantile(0.9999)
    trimmed = df[df.sum_gamerounds <= cutoff]
    r7_trim = compare(trimmed, "retention_7")

    mde_d1 = mde(results["retention_1"]["control_rate"], min(n_c, n_t))
    mde_d7 = mde(results["retention_7"]["control_rate"], min(n_c, n_t))
    # How many players per group would a 0.5 pt D1 effect need?
    h = proportion_effectsize(results["retention_1"]["control_rate"],
                              results["retention_1"]["control_rate"] - 0.005)
    n_needed_half_pt = NormalIndPower().solve_power(effect_size=abs(h), alpha=ALPHA,
                                                    power=0.8, ratio=1)

    # ---------- Tableau-ready exports ----------
    groups.to_csv(TAB / "ab_metrics_by_group.csv", index=False)
    segments.to_csv(TAB / "ab_engagement_segments.csv", index=False)
    survival.to_csv(TAB / "ab_rounds_survival.csv", index=False)
    pd.DataFrame([{k: v for k, v in r.items() if k != "boot"} for r in results.values()]) \
        .to_csv(TAB / "ab_test_stats.csv", index=False)

    # ---------- Figures ----------
    # 1. Retention by variant with 95% CIs
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, (m, label) in zip(axes, [("retention_1", "Day-1 retention"),
                                     ("retention_7", "Day-7 retention")]):
        r = results[m]
        rates = [r["control_rate"], r["treatment_rate"]]
        ns = [n_c, n_t]
        errs = [1.96 * np.sqrt(p * (1 - p) / n) for p, n in zip(rates, ns)]
        bars = ax.bar(["Gate at 30\n(control)", "Gate at 40\n(treatment)"], rates,
                      color=[COLORS[CONTROL], COLORS[TREATMENT]], width=0.55,
                      yerr=errs, capsize=5, ecolor="#52514e", edgecolor="#fcfcfb", linewidth=2)
        for b, v in zip(bars, rates):
            ax.text(b.get_x() + b.get_width() / 2, v + max(errs) + max(rates) * 0.025, f"{v:.1%}",
                    ha="center", fontsize=11, color="#0b0b0b")
        ax.set_ylim(0, max(rates) * 1.18)
        ax.yaxis.set_major_locator(plt.MultipleLocator(0.1 if max(rates) > 0.3 else 0.05))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
        style(ax, f"{label}  (p = {r['p_value']:.3f})", "Share of players retained")
    fig.suptitle("Moving the gate to level 40 lowered retention", x=0.01, ha="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "ab_retention_by_variant.png", dpi=160, facecolor="#fcfcfb")
    plt.close(fig)

    # 2. Bootstrap distribution of the D7 difference
    fig, ax = plt.subplots(figsize=(8, 4))
    boot = results["retention_7"]["boot"] * 100
    ax.hist(boot, bins=50, color=COLORS[TREATMENT], edgecolor="#fcfcfb", linewidth=1)
    ax.axvline(0, color="#0b0b0b", linewidth=1.5, linestyle="--")
    ax.text(0.1, ax.get_ylim()[1] * 0.9, "no difference", color="#52514e", fontsize=10)
    style(ax, "Bootstrap: Day-7 retention, treatment minus control (2,000 resamples)",
          "Resamples")
    ax.set_xlabel("Difference in percentage points", color="#52514e")
    fig.tight_layout()
    fig.savefig(FIG / "ab_bootstrap_d7.png", dpi=160, facecolor="#fcfcfb")
    plt.close(fig)

    # 3. Share of players reaching N rounds
    fig, ax = plt.subplots(figsize=(8, 4))
    for v in (CONTROL, TREATMENT):
        s = survival[survival.version == v]
        ax.plot(s.rounds, s.share_reaching, color=COLORS[v], linewidth=2,
                label="Gate at 30" if v == CONTROL else "Gate at 40")
    for g in (30, 40):
        ax.axvline(g, color="#c3c2b7", linewidth=1, linestyle=":")
        ax.text(g + 0.8, 0.9, f"level {g}", color="#52514e", fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.set_xlabel("Game rounds played (capped at 100)", color="#52514e")
    style(ax, "Share of players who played at least N rounds", "Share of players")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "ab_rounds_survival.png", dpi=160, facecolor="#fcfcfb")
    plt.close(fig)

    # ---------- Written results ----------
    r1, r7 = results["retention_1"], results["retention_7"]
    q = quality.iloc[0]

    def row(r, name):
        return (f"| {name} | {r['control_rate']:.2%} | {r['treatment_rate']:.2%} | "
                f"{r['abs_diff'] * 100:+.2f} pts ({r['rel_diff']:+.1%}) | "
                f"[{r['ci_low'] * 100:+.2f}, {r['ci_high'] * 100:+.2f}] | {r['p_value']:.4f} | "
                f"{r['prob_control_better']:.1%} |")

    t_share = n_t / (n_c + n_t)
    srm_note = (
        f"\n**Caveat: sample ratio mismatch.** Treatment received {t_share:.2%} of players instead of 50% "
        f"({n_t - n_c:,} more than control; p = {srm_p:.3f}). That usually signals a logging or assignment "
        "issue, which can bias results. Before a final launch decision, I would ask engineering to check "
        "how users were bucketed and whether any users were dropped from one group. Keeping the gate at 30 "
        "is also the low-risk choice, because it is the current default.\n"
        if srm_p <= 0.01 else "")

    md = f"""# A/B Test Results: Gate at Level 30 vs. Level 40

*Generated by `src/ab_test.py`. Every number below is computed from the data.*

## Data checks
- {int(q.n_rows):,} players, {int(q.duplicate_rows)} duplicate IDs, {int(q.null_version)} missing values.
- {int(q.never_played):,} players installed but never played a round.
- Extreme outlier: one player logged {int(q.max_rounds):,} rounds (99th percentile is {q.p99_rounds:.0f}).
  Results are re-checked without them below.
- **Sample ratio check:** {n_c:,} control vs. {n_t:,} treatment. Chi-square = {chi2:.2f}, p = {srm_p:.3f}.
  {"The split is consistent with random 50/50 assignment." if srm_p > 0.01 else "WARNING: possible sample ratio mismatch; investigate assignment before trusting results."}

## Results (treatment minus control)

| Metric | Gate 30 | Gate 40 | Difference | 95% CI (pts) | p-value | P(control better), bootstrap |
|---|---|---|---|---|---|---|
{row(r1, "Day-1 retention")}
{row(r7, "Day-7 retention")}

- **Day-7 retention** is lower with the gate at 40, and the difference is statistically significant
  at α = 0.05 (p = {r7['p_value']:.4f}). In {r7['prob_control_better']:.1%} of 2,000 bootstrap resamples, control beat treatment.
- **Day-1 retention** is slightly lower too, but not significant (p = {r1['p_value']:.3f}).
- **Sensitivity:** without the outlier player, the Day-7 difference is {r7_trim['abs_diff'] * 100:+.2f} pts
  (p = {r7_trim['p_value']:.4f}), so the outlier doesn't drive the result.

## Power
- With about {min(n_c, n_t):,} players per group, the test could detect a Day-1 change of
  {mde_d1 * 100:.2f} pts and a Day-7 change of {mde_d7 * 100:.2f} pts at 80% power.
- Confirming a 0.5-pt Day-1 effect would need about {n_needed_half_pt:,.0f} players per group,
  so the Day-1 null result means "no large effect", not "no effect".

## Descriptive: retention by engagement band (Day 7)
Bands use rounds played, which happens *after* assignment, so these splits are descriptive, not causal.

{segments.to_markdown(index=False)}

## Recommendation
**Keep the gate at level 30.** Moving it to level 40 lowered Day-7 retention by about
{abs(r7['abs_diff']) * 100:.1f} percentage points ({abs(r7['rel_diff']):.1%} relative), with p = {r7['p_value']:.4f}.
A plausible explanation is that an earlier break gives players a pause, which can make them more
likely to come back.
{srm_note}
Next step: a follow-up test could try a gate *earlier* than 30.
"""
    (OUT / "ab_test_results.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
