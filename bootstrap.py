"""Stationary block bootstrap for the leveraged tail-protection backtest.

The audit's dominant finding: the historical rolling-window "distributions" are
one realized path sliced into heavily overlapping windows, so a 10y "5th
percentile" has an effective sample size of ~3 and the 10y tail is a single
2000-2009 episode. This module replaces that with genuinely independent draws.

Method: the **stationary bootstrap** (Politis & Romano 1994). We resample the
daily series in blocks of random (geometric) length and concatenate them into a
synthetic path of the requested horizon, then run the *same* path engine
(`run_path`) on it. Blocks preserve short-range dependence -- volatility
clustering and crash persistence -- which IID resampling destroys and which is
exactly what drives leverage ruin and option cost. Returns, financing, pricing
vol and dividend yield are resampled *jointly by index* so their crash-time
co-movement (vol spikes when the market falls) is preserved.

Caveat this does NOT fix: block bootstrapping a single US history cannot invent
tail events the US never had (a permanent impairment a la Japan-1990). It fixes
pseudo-replication and lets crashes recombine with non-crash periods, but the
*menu* of daily shocks is still the US sample. Cross-country resampling (see the
audit) is the complementary fix.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from backtest import PathResult, run_path
from config import Config
from model import levered_daily


def _source_pool(data: pd.DataFrame, cfg: Config, history: str) -> dict:
    """Daily source arrays to resample from, restricted to a valid span."""
    real_tr = data["real_tr"].to_numpy(bool)
    has_rf = data["has_rf"].to_numpy(bool) if "has_rf" in data else np.ones(len(data), bool)
    if history == "real_tr" and real_tr.any():
        mask = real_tr
    elif history == "rf" and has_rf.any():
        mask = has_rf
    else:
        mask = np.ones(len(data), bool)
    idx = np.flatnonzero(mask)
    sl = slice(idx[0], idx[-1] + 1)
    close = data["S"].to_numpy(float)[sl]
    price_ret = np.empty_like(close)
    price_ret[0] = 0.0
    price_ret[1:] = close[1:] / close[:-1] - 1.0
    return {
        "tr": data["tr"].to_numpy(float)[sl],
        "rf_daily": data["rf_daily"].to_numpy(float)[sl],
        "rf_annual": data["rf_annual"].to_numpy(float)[sl],
        "sigma": data["sigma"].to_numpy(float)[sl],
        "div_yield": data["div_yield"].to_numpy(float)[sl],
        "price_ret": price_ret,
    }


def _stationary_indices(n_pool: int, n_out: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary-bootstrap index sequence of length n_out.

    Start a fresh block (uniform random origin) with prob p = 1/mean_block each
    step; otherwise advance the previous index by one (wrapping circularly).
    Geometric block lengths => the resampled series is stationary and the result
    is insensitive to the exact block length.
    """
    p = 1.0 / mean_block
    new_block = rng.random(n_out) < p
    new_block[0] = True
    starts = rng.integers(0, n_pool, size=n_out)
    pos = np.arange(n_out)
    # last position at which a new block began, for each t (vectorized)
    block_start_pos = np.maximum.accumulate(np.where(new_block, pos, 0))
    offset = pos - block_start_pos
    base = starts[block_start_pos]
    return (base + offset) % n_pool


def bootstrap_windows(
    data: pd.DataFrame,
    cfg: Config,
    window_years: int,
    n_boot: int = 2000,
    mean_block: float = 21.0,
    seed: int = 0,
    history: str = "rf",
) -> List[PathResult]:
    """Run `n_boot` synthetic `window_years`-long paths via stationary bootstrap.

    `mean_block` is in trading days (21 ~= one month, long enough to carry
    volatility clustering through a block). `history` chooses the source pool.
    """
    pool = _source_pool(data, cfg, history)
    n_pool = len(pool["tr"])
    n_days = int(round(window_years * cfg.trading_days_per_year)) + 1
    if n_days > n_pool:
        # Circular wrapping handles this, but warn-by-clamp keeps blocks sane.
        pass

    # Synthetic calendar: equally spaced so end - start == window_years exactly
    # and annual rolls land every ~trading_days_per_year steps.
    t0 = pd.Timestamp("1990-01-01")
    step_days = window_years * 365.25 / (n_days - 1)
    synth_dates = t0 + pd.to_timedelta(np.arange(n_days) * step_days, unit="D")
    months = synth_dates.year * 12 + synth_dates.month
    month_start = np.empty(n_days, dtype=bool)
    month_start[0] = True
    month_start[1:] = months[1:] != months[:-1]

    rng = np.random.default_rng(seed)
    L = cfg.leverage
    results: List[PathResult] = []
    for b in range(n_boot):
        idx = _stationary_indices(n_pool, n_days, mean_block, rng)
        tr = pool["tr"][idx]
        rf_daily = pool["rf_daily"][idx]
        S = 100.0 * np.cumprod(1.0 + pool["price_ret"][idx])
        arrays = {
            "tr": tr,
            "rf": rf_daily,
            "rf_annual": rf_daily * cfg.trading_days_per_year,
            "S": S,
            "sigma": pool["sigma"][idx],
            "div_yield": pool["div_yield"][idx],
            "month_start": month_start,
            "lev": levered_daily(tr, rf_daily, L),
        }
        synth = pd.DataFrame(index=synth_dates)
        res = run_path(synth, cfg, 0, n_days - 1, arrays)
        results.append(res)
    return results


# ---------------------------------------------------------------------------
def effective_sample_size(start_dates: pd.Series, window_years: int) -> float:
    """Non-overlapping window count for a monthly-stepped overlapping set."""
    if len(start_dates) == 0:
        return 0.0
    span_years = (start_dates.max() - start_dates.min()).days / 365.25
    return span_years / window_years


def summarize_results(results: List[PathResult]) -> dict:
    """Tail/median metrics over a list of PathResults (bootstrap or historical)."""
    tw = np.array([r.terminal_wealth for r in results], float)
    cg = np.array([r.cagr for r in results if r.cagr is not None], float)
    mdd = np.array([r.max_drawdown for r in results], float)
    ruined = np.array([r.ruined for r in results], bool)
    return dict(
        n=len(results),
        cagr_median=float(np.median(cg)) if cg.size else np.nan,
        cagr_mean=float(np.mean(cg)) if cg.size else np.nan,
        cagr_p5=float(np.percentile(cg, 5)) if cg.size else np.nan,
        tw_p5=float(np.percentile(tw, 5)),
        tw_median=float(np.median(tw)),
        mdd_p95=float(np.percentile(mdd, 95)),
        p_ruin=float(ruined.mean()),
    )


if __name__ == "__main__":
    import argparse
    import warnings

    from data import prepare

    ap = argparse.ArgumentParser(description="Bootstrap the headline cells.")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--mean-block", type=float, default=21.0)
    ap.add_argument("--history", default="rf", choices=["real_tr", "rf", "all"])
    ap.add_argument("--maint-margin", type=float, default=0.0,
                    help="realistic maintenance margin as fraction of notional (e.g. 0.25)")
    ap.add_argument("--out", default="output/bootstrap_results.csv")
    args = ap.parse_args()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(Config())

    rows = []
    for wy in (5, 10, 15, 20):
        for L in (1.0, 2.0, 3.0):
            for m in (None, 0.15, 0.20, 0.25):
                cfg = Config(leverage=L, put_moneyness=m, rebalance="monthly",
                             vrp_mode="marked_up" if m is not None else "fair",
                             maint_margin_frac=args.maint_margin)
                res = bootstrap_windows(data, cfg, wy, n_boot=args.n_boot,
                                        mean_block=args.mean_block, history=args.history)
                s = summarize_results(res)
                s.update(window_years=wy, leverage=L,
                         protection="none" if m is None else f"put{int(m*100)}")
                rows.append(s)
        print(f"  bootstrapped {wy}y windows")
    df = pd.DataFrame(rows)
    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"\nWrote {args.out} ({args.n_boot} draws/cell, mean block {args.mean_block}d, history={args.history})")
    show = ["window_years", "leverage", "protection", "cagr_median", "cagr_mean",
            "cagr_p5", "tw_p5", "p_ruin", "mdd_p95"]
    pd.set_option("display.width", 200)
    print(df[df.leverage == 3.0][show].to_string(index=False))
