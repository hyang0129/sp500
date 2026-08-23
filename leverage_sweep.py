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


if __name__ == "__main__":
    main()
