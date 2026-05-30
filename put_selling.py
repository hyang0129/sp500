"""Put-WRITING overlay: 1x futures + SHORT 30-day cash-settled puts, harvesting
the volatility risk premium. Sweeps strike (ATM/5%/10% OTM) x notional ratio
(0.25..1.0) x horizon, via the stationary bootstrap, under a realistic 10%
maintenance margin. Premiums are marked-up (vol x1.2) -- the rich price a seller
actually collects -- with a fair-priced control.

Writes output/put_selling.csv (+ .png) and prints the 1x tables.
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

STRIKES = {"ATM": 0.0, "5%OTM": 0.05, "10%OTM": 0.10}
RATIOS = [0.25, 0.5, 0.75, 1.0]
HORIZONS = [5, 10, 20]
N_BOOT = 800
MAINT = 0.10
T30 = 1.0 / 12.0  # 30-day tenor


def build() -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(Config())
    rows = []
    # naked 1x baseline per horizon
    for wy in HORIZONS:
        cfg = Config(leverage=1.0, put_moneyness=None, rebalance="monthly",
                     maint_margin_frac=MAINT)
        s = summarize_results(bootstrap_windows(data, cfg, wy, n_boot=N_BOOT, history="rf", seed=5))
        s.update(window_years=wy, strike="none", ratio=0.0, vrp="-")
        rows.append(s)
    # short-put sweep
    for vrp in ("marked_up", "fair"):
        for sk, m in STRIKES.items():
            for ratio in RATIOS:
                for wy in HORIZONS:
                    cfg = Config(leverage=1.0, put_side="sell", put_moneyness=m,
                                 put_ratio=ratio, roll_period_years=T30,
                                 rebalance="monthly", vrp_mode=vrp,
                                 maint_margin_frac=MAINT)
                    s = summarize_results(bootstrap_windows(data, cfg, wy, n_boot=N_BOOT,
                                                            history="rf", seed=5))
                    s.update(window_years=wy, strike=sk, ratio=ratio, vrp=vrp)
                    rows.append(s)
        print(f"  done vrp={vrp}")
    return pd.DataFrame(rows)


def plot(df, path):
    d = df[(df.vrp != "fair")]
    fig, axes = plt.subplots(1, len(HORIZONS), figsize=(6.5 * len(HORIZONS), 5.5), sharey=False)
    for ax, wy in zip(axes, HORIZONS):
        base = d[(d.window_years == wy) & (d.strike == "none")].iloc[0]
        for sk, color in [("ATM", "firebrick"), ("5%OTM", "darkorange"), ("10%OTM", "seagreen")]:
            sub = d[(d.window_years == wy) & (d.strike == sk)].sort_values("ratio")
            ax.plot(sub.tw_p5, sub.tw_median, "o-", color=color, label=sk)
            for _, r in sub.iterrows():
                ax.annotate(f"{r.ratio:g}", (r.tw_p5, r.tw_median), fontsize=7,
                            xytext=(3, 3), textcoords="offset points", color=color)
        ax.scatter([base.tw_p5], [base.tw_median], color="black", zorder=5, s=60, marker="*")
        ax.annotate("naked 1x", (base.tw_p5, base.tw_median), fontsize=8,
                    xytext=(4, -10), textcoords="offset points")
        ax.set_title(f"{wy}-year horizon")
        ax.set_xlabel("5th-pct terminal wealth (tail)  ->safer right")
        ax.set_ylabel("median terminal wealth (growth)")
        ax.legend(title="short-put strike", fontsize=8)
    fig.suptitle("Selling 30-day puts on 1x futures: growth vs tail, by strike & notional ratio "
                 "(labels)\n10% maint margin, marked-up premiums, bootstrap 1934-2026  (* = no puts)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    df = build()
    cols = ["window_years", "strike", "ratio", "vrp", "cagr_median", "cagr_mean",
            "cagr_p5", "tw_median", "tw_p5", "mdd_p95", "p_ruin"]
    df = df[cols]
    df.to_csv("output/put_selling.csv", index=False)
    plot(df, "output/put_selling.png")
    pd.set_option("display.width", 220)
    for wy in HORIZONS:
        print(f"\n===== {wy}y | 1x futures + SHORT 30-day puts | marked-up | 10% margin =====")
        t = df[(df.window_years == wy) & ((df.vrp == "marked_up") | (df.strike == "none"))]
        print(t.drop(columns=["window_years", "vrp"]).to_string(index=False))
    print("\nWrote output/put_selling.csv and output/put_selling.png")
