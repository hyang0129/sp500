"""Where is the optimal leverage on the S&P itself?

The put study (SUMMARY.md) asked whether protection helps at a *given* leverage.
This asks the prior question: held unprotected, what leverage maximises long-run
outcomes — and by which criterion?

Three criteria, because they disagree sharply:
    median log-wealth  -- the growth-optimal ("Kelly-ish") point
    5th-pct wealth     -- the survival/tail-optimal point
    median CAGR / DD   -- return per unit of pain

The answer depends far more on **rebalance frequency** than most discussions
admit: a monthly-reset futures book suffers much less volatility decay than a
daily-reset LETF, so its optimum sits far higher.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from backtest import rolling_windows
from config import Config
from data import prepare

LEVERAGES = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0]


def sweep(data, window_years: int, rebalance: str, step_months: int = 3,
          require_real_tr: bool = False, maintenance_rate: float = 0.065,
          include_dead: bool = True) -> pd.DataFrame:
    """Leverage sweep keeping DEAD windows in the distribution.

    A liquidated window has terminal wealth 0, so its CAGR is exactly -100%
    (0**(1/T) - 1 = -1). Dropping those windows and taking the median of the
    survivors is survivorship bias — it makes high leverage look better the
    more often it kills you. With include_dead=True they are carried at -100%.

    require_real_tr=False uses the full 1976-2026 sample so that October 1987
    (the worst month ever for a leveraged book) is in scope.
    """
    rows = []
    for L in LEVERAGES:
        cfg = Config(leverage=L, put_moneyness=None, rebalance=rebalance,
                     maintenance_rate=maintenance_rate)
        rs = rolling_windows(data, cfg, window_years=window_years,
                             step_months=step_months, require_real_tr=require_real_tr)
        if include_dead:
            cg = np.array([-1.0 if r.ruined else r.cagr for r in rs])
        else:
            cg = np.array([r.cagr for r in rs if r.cagr is not None])
        tw = np.array([r.terminal_wealth for r in rs])
        dd = np.array([r.max_drawdown for r in rs])
        rows.append(dict(
            L=L, n=len(rs),
            medCAGR=np.median(cg), p5CAGR=np.percentile(cg, 5),
            medTW=np.median(tw), p5TW=np.percentile(tw, 5),
            medlogW=np.median(np.log(np.maximum(tw, 1e-12))),
            medDD=np.median(dd), maxDD=dd.max(),
            p_ruin=np.mean([r.ruined for r in rs]),
        ))
    return pd.DataFrame(rows)


def optima(df: pd.DataFrame) -> dict:
    return {
        "median CAGR": df.loc[df.medCAGR.idxmax(), "L"],
        "5th-pct CAGR": df.loc[df.p5CAGR.idxmax(), "L"],
        "growth (median log-wealth)": df.loc[df.medlogW.idxmax(), "L"],
        "tail (5th-pct wealth)": df.loc[df.p5TW.idxmax(), "L"],
    }


def main():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(Config())
    print("Dead (liquidated) windows are KEPT in the distribution at CAGR = -100%,")
    print("terminal wealth = 0. Maintenance margin 6.5% of notional. Sample 1976-2026,")
    print("so October 1987 is in scope.\n")
    for rebalance in ("monthly", "daily"):
        for wy in (10, 20):
            df = sweep(data, wy, rebalance)
            print(f"\n=== {wy}-year windows, {rebalance} reset (n={int(df.n.iloc[0])}) ===")
            print(df.drop(columns=["n"]).to_string(index=False,
                                                   float_format=lambda v: f"{v:,.3f}"))
            for k, v in optima(df).items():
                print(f"    optimal L by {k:28s}: {v}")

    print("\n=== 10-year windows: MONTHLY vs DAILY reset, 1x-3x by 0.25 ===")
    cmp = compare_resets(data, window_years=10)
    print(cmp.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
    chart_resets(cmp)


def compare_resets(data, window_years: int = 10, step_months: int = 1,
                   leverages=None, maintenance_rate: float = 0.065) -> pd.DataFrame:
    """Monthly vs daily reset, side by side, dead windows kept at -100%."""
    leverages = leverages or [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0]
    rows = []
    for L in leverages:
        row = {"L": L}
        for reb, tag in (("monthly", "m"), ("daily", "d")):
            cfg = Config(leverage=L, put_moneyness=None, rebalance=reb,
                         maintenance_rate=maintenance_rate)
            rs = rolling_windows(data, cfg, window_years=window_years,
                                 step_months=step_months, require_real_tr=False)
            cg = np.array([-1.0 if r.ruined else r.cagr for r in rs])
            tw = np.array([r.terminal_wealth for r in rs])
            dd = np.array([r.max_drawdown for r in rs])
            row[f"{tag}_med"] = np.median(cg)
            row[f"{tag}_p5"] = np.percentile(cg, 5)
            row[f"{tag}_p5TW"] = np.percentile(tw, 5)
            row[f"{tag}_DD"] = np.median(dd)
            row[f"{tag}_ruin"] = np.mean([r.ruined for r in rs])
            row["n"] = len(rs)
        rows.append(row)
    return pd.DataFrame(rows)


def chart_resets(df: pd.DataFrame, window_years: int = 10,
                 path: str = "output/reset_comparison.png"):
    import os
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(15, 4.8))
    a1.plot(df.L, df.m_med * 100, "o-", color="steelblue", label="monthly")
    a1.plot(df.L, df.d_med * 100, "s-", color="darkorange", label="daily")
    a1.set_title(f"median CAGR ({window_years}y windows)")
    a2.plot(df.L, df.m_p5 * 100, "o-", color="steelblue", label="monthly")
    a2.plot(df.L, df.d_p5 * 100, "s-", color="darkorange", label="daily")
    a2.set_ylim(-40, 10)
    a2.set_title("5th-pct CAGR (dead windows = -100%)")
    a3.plot(df.L, df.m_p5TW, "o-", color="steelblue", label="monthly")
    a3.plot(df.L, df.d_p5TW, "s-", color="darkorange", label="daily")
    a3.axhline(1.0, color="grey", ls="--", lw=0.8)
    a3.set_title("5th-pct terminal wealth (x)")
    cliff = df[df.m_ruin > 0].L.min() if (df.m_ruin > 0).any() else None
    for ax in (a1, a2, a3):
        if cliff:
            ax.axvspan(cliff - 0.125, df.L.max() + 0.1, color="red", alpha=0.10)
        ax.set_xlabel("leverage")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("Monthly vs daily reset — red band = monthly reset starts getting "
                 "margin-called (dead windows kept in the distribution)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
