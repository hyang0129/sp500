"""Leverage frontier: geometric growth vs. tail vs. ruin across a fine leverage
grid, via the stationary bootstrap. Answers 'what leverage is the best
risk/reward balance, and where does the ruin cliff start?'

Writes output/leverage_frontier.csv and output/leverage_frontier.png.
"""
from __future__ import annotations

import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from bootstrap import bootstrap_windows, summarize_results  # noqa: E402
from config import Config  # noqa: E402
from data import prepare  # noqa: E402

LEVS = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
HORIZONS = [5, 20]
MAINT = 0.10  # realistic maintenance margin (fraction of notional)


def build(n_boot=1000, history="rf", seed=3) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(Config())
    rows = []
    for wy in HORIZONS:
        for L in LEVS:
            cfg = Config(leverage=L, put_moneyness=None, rebalance="monthly",
                         maint_margin_frac=MAINT)
            s = summarize_results(bootstrap_windows(data, cfg, wy, n_boot=n_boot,
                                                    history=history, seed=seed))
            s.update(window_years=wy, leverage=L)
            rows.append(s)
    return pd.DataFrame(rows)


def plot(df: pd.DataFrame, path: str):
    fig, axes = plt.subplots(1, len(HORIZONS), figsize=(7 * len(HORIZONS), 5.5))
    for ax, wy in zip(axes, HORIZONS):
        d = df[df.window_years == wy].sort_values("leverage")
        ax2 = ax.twinx()
        l1, = ax.plot(d.leverage, d.tw_median, "o-", color="seagreen", label="median wealth (growth)")
        l2, = ax.plot(d.leverage, d.tw_p5, "s-", color="firebrick", label="5th-pct wealth (tail)")
        l3, = ax2.plot(d.leverage, d.p_ruin * 100, "^--", color="dimgray", label="P(ruin) %")
        ax.axhline(1.0, color="grey", lw=0.7, ls=":")
        # mark growth-optimal leverage (max median wealth)
        Lstar = d.loc[d.tw_median.idxmax(), "leverage"]
        ax.axvline(Lstar, color="seagreen", lw=0.8, ls="--", alpha=0.6)
        ax.set_title(f"{wy}-year horizon  (growth-optimal L* = {Lstar:g}x)")
        ax.set_xlabel("leverage")
        ax.set_ylabel("terminal wealth (×)")
        ax2.set_ylabel("P(ruin) (%)")
        ax.legend(handles=[l1, l2, l3], loc="upper left", fontsize=9)
    fig.suptitle(f"Leverage risk/reward frontier — {MAINT:.0%} maintenance margin, "
                 "no puts, stationary bootstrap of 1934-2026")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    df = build()
    df = df[["window_years", "leverage", "cagr_median", "cagr_mean", "cagr_p5",
             "tw_median", "tw_p5", "p_ruin"]]
    df.to_csv("output/leverage_frontier.csv", index=False)
    plot(df, "output/leverage_frontier.png")
    pd.set_option("display.width", 200)
    print(df.to_string(index=False))
    print("\nWrote output/leverage_frontier.csv and output/leverage_frontier.png")
