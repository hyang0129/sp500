"""Run the §4 experiment grid and emit a tidy per-window results table.

Grid (cartesian product):
    leverage    in {1, 2, 3}
    protection  in {none, put@15%, put@20%, put@25%}
    rebalance   in {monthly, daily}
    vrp_mode    in {fair, marked_up}
    liquidation = daily_path (default)

Each cell is evaluated over every rolling 10y and 20y window (monthly step),
yielding a distribution of outcomes. Output: output/results.csv (one row per
window per cell).
"""
from __future__ import annotations

import itertools
import os
import time
import warnings
from dataclasses import asdict, replace

import pandas as pd

from backtest import rolling_windows
from config import Config
from data import prepare

LEVERAGES = [1.0, 2.0, 3.0]
MONEYNESS = [None, 0.15, 0.20, 0.25]
REBALANCE = ["monthly", "daily"]
VRP_MODES = ["fair", "marked_up"]
WINDOWS = [10, 20]


def run_grid(
    base: Config | None = None,
    step_months: int = 1,
    out_path: str = "output/results.csv",
    progress: bool = True,
) -> pd.DataFrame:
    base = base or Config()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(base)

    rows = []
    cells = list(itertools.product(LEVERAGES, MONEYNESS, REBALANCE, VRP_MODES))
    t0 = time.time()
    for ci, (L, m, reb, vrp) in enumerate(cells):
        # vrp_mode is irrelevant with no protection -> run only once ("fair").
        if m is None and vrp != "fair":
            continue
        cfg = replace(base, leverage=L, put_moneyness=m, rebalance=reb, vrp_mode=vrp)
        for wy in WINDOWS:
            results = rolling_windows(data, cfg, window_years=wy, step_months=step_months)
            prot = "none" if m is None else f"put{int(m*100)}"
            for r in results:
                rows.append(
                    dict(
                        leverage=L,
                        protection=prot,
                        moneyness=(0.0 if m is None else m),
                        rebalance=reb,
                        vrp_mode=(vrp if m is not None else "none"),
                        window_years=wy,
                        start=r.start,
                        end=r.end,
                        terminal_wealth=r.terminal_wealth,
                        cagr=r.cagr,
                        max_drawdown=r.max_drawdown,
                        ruined=r.ruined,
                        log_terminal=r.log_terminal,
                    )
                )
        if progress:
            print(f"[{ci+1}/{len(cells)}] {cfg.label():32s}  ({time.time()-t0:5.1f}s)")

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\nWrote {out_path}: {len(df)} window-rows across {df.groupby(['leverage','protection','rebalance','vrp_mode','window_years']).ngroups} cells")
    return df


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Run the leverage x protection experiment grid.")
    ap.add_argument("--step-months", type=int, default=1, help="rolling-window step (months)")
    ap.add_argument("--out", default="output/results.csv")
    ap.add_argument("--liquidation", default="daily_path", choices=["daily_path", "month_end"])
    ap.add_argument("--div-yield", type=float, default=0.018)
    args = ap.parse_args()

    base = Config(liquidation_model=args.liquidation, div_yield=args.div_yield)
    run_grid(base, step_months=args.step_months, out_path=args.out)
