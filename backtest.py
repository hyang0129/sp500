"""Single-path simulation and the rolling-window driver.

A "path" runs the levered, optionally put-protected account over one historical
window. The driver re-runs it over every rolling 10y/20y start date so we get a
*distribution* of outcomes per configuration (sequence-of-returns risk is the
whole point).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from config import Config
from model import bs_put, levered_daily, segment_equity_path


@dataclass
class PathResult:
    start: pd.Timestamp
    end: pd.Timestamp
    years: float
    terminal_wealth: float          # equity multiple (start = 1.0)
    cagr: Optional[float]           # None if ruined
    max_drawdown: float             # fraction (0..1)
    ruined: bool
    log_terminal: float             # log(terminal_wealth); -inf treated below
    curve: Optional[pd.Series] = None  # daily equity path (if record_curve)


def _roll_indices(dates: pd.DatetimeIndex, start_i: int, end_i: int, period_years: float) -> List[int]:
    """Indices of annual roll dates anchored at the window start.

    Roll k lands on the first trading day on/after start + k*period. The final
    roll is forced to the window end so the last put is always settled there.
    """
    d0 = dates[start_i]
    end_date = dates[end_i]
    rolls = [start_i]
    k = 1
    while True:
        anniv = d0 + pd.DateOffset(years=int(round(k * period_years)))
        if anniv >= end_date:
            break
        j = int(dates.searchsorted(anniv, side="left"))
        j = min(max(j, rolls[-1] + 1), end_i)
        if j > rolls[-1]:
            rolls.append(j)
        k += 1
    if rolls[-1] != end_i:
        rolls.append(end_i)
    return rolls


def run_path(
    data: pd.DataFrame,
    cfg: Config,
    start_i: int,
    end_i: int,
    arrays: Optional[dict] = None,
    record_curve: bool = False,
) -> PathResult:
    """Simulate one window [start_i, end_i] (inclusive indices into `data`)."""
    dates = data.index
    curve_idx: List[int] = []
    curve_val: List[float] = []
    if arrays is None:
        arrays = build_arrays(data, cfg)
    tr = arrays["tr"]
    rf = arrays["rf"]
    S = arrays["S"]
    sigma = arrays["sigma"]
    rf_annual = arrays["rf_annual"]
    month_start = arrays["month_start"]
    lev = arrays["lev"]  # precomputed for cfg.leverage

    L = cfg.leverage
    m = cfg.put_moneyness
    protect_full = cfg.protect_notional == "full"
    q = cfg.div_yield
    T = cfg.roll_period_years
    daily_check = cfg.liquidation_model == "daily_path" or cfg.rebalance == "daily"
    maint = cfg.maintenance_frac

    rolls = _roll_indices(dates, start_i, end_i, T)

    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    ruined = False
    put_units = 0.0
    put_K = 0.0

    for k in range(len(rolls)):
        i = rolls[k]
        # 1) Settle the put bought at the previous roll (payoff at expiry).
        if put_units > 0.0 and not ruined:
            payoff = max(put_K - S[i], 0.0) * put_units
            equity += payoff
        put_units = 0.0
        if record_curve:
            curve_idx.append(i)
            curve_val.append(max(equity, 0.0))

        if k == len(rolls) - 1:
            break  # final roll: window ends, nothing more to do

        # 2) Buy protection for the coming year (premium paid now).
        if m is not None and not ruined and equity > 0.0:
            Si = S[i]
            K = (1.0 - m) * Si
            notional = (L if protect_full else 1.0) * equity
            units = notional / Si
            eff_sigma = sigma[i] * (cfg.vrp_markup if cfg.vrp_mode == "marked_up" else 1.0)
            price = bs_put(Si, K, T, rf_annual[i], eff_sigma, q)
            equity -= price * units
            if equity <= maint:
                ruined = True
                equity = 0.0
            else:
                put_units = units
                put_K = K

        # 3) Run the leverage engine over the segment [i, rolls[k+1]].
        a, b = i + 1, rolls[k + 1] + 1  # daily returns from day after roll to next roll
        if ruined or a >= b:
            continue
        seg_lev = lev[a:b]
        seg_ms = month_start[a:b]
        path, base = segment_equity_path(equity, seg_lev, seg_ms, cfg.rebalance,
                                         return_base=True)
        # A broker liquidates at the maintenance level, not at zero equity.
        # Exposure notional is L * base, so the floor is rate * L * base.
        floor = np.full_like(path, maint)
        if cfg.maintenance_rate > 0.0:
            floor = np.maximum(floor, cfg.maintenance_rate * L * base)

        # 4) Liquidation scan (absorbing zero) + drawdown tracking.
        check_path = path
        if cfg.put_mtm_for_liquidation and put_units > 0.0:
            # Cheap mark-to-market: credit the put's intrinsic value each day.
            intrinsic = np.maximum(put_K - S[a:b], 0.0) * put_units
            check_path = path + intrinsic

        breach = np.flatnonzero(check_path <= floor)
        if breach.size > 0 and daily_check:
            first = breach[0]
            path = path.copy()
            path[first:] = 0.0
            ruined = True
        elif breach.size > 0 and not daily_check:
            # month_end model: only liquidate if a *month-end* mark breaches.
            ms_idx = np.flatnonzero(seg_ms)
            month_ends = np.append(ms_idx[1:] - 1, len(path) - 1) if ms_idx.size else np.array([len(path) - 1])
            bad = month_ends[check_path[month_ends] <= floor[month_ends]]
            if bad.size > 0:
                first = int(bad[0])
                path = path.copy()
                path[first:] = 0.0
                ruined = True

        # drawdown over the segment
        run_peak = np.maximum.accumulate(path)
        run_peak = np.maximum(run_peak, peak)
        dd = 1.0 - path / run_peak
        seg_max_dd = float(np.nanmax(dd)) if path.size else 0.0
        if seg_max_dd > max_dd:
            max_dd = seg_max_dd
        peak = max(peak, float(path.max()))
        equity = float(path[-1])
        if equity <= maint:
            ruined = True
            equity = 0.0
        if record_curve:
            curve_idx.extend(range(a, b))
            curve_val.extend(path.tolist())

    years = (dates[end_i] - dates[start_i]).days / 365.25
    terminal = max(equity, 0.0)
    if ruined or terminal <= 0.0:
        cagr = None
        log_terminal = -np.inf
        terminal = 0.0
        ruined = True
    else:
        cagr = terminal ** (1.0 / years) - 1.0
        log_terminal = float(np.log(terminal))

    curve = None
    if record_curve and curve_idx:
        curve = pd.Series(curve_val, index=dates[curve_idx]).sort_index()
        curve = curve[~curve.index.duplicated(keep="last")]

    return PathResult(
        start=dates[start_i],
        end=dates[end_i],
        years=years,
        terminal_wealth=terminal,
        cagr=cagr,
        max_drawdown=max_dd,
        ruined=ruined,
        log_terminal=log_terminal,
        curve=curve,
    )


def build_arrays(data: pd.DataFrame, cfg: Config) -> dict:
    """Pull numpy arrays out of the frame once (avoids pandas in the hot loop)."""
    tr = data["tr"].to_numpy(float)
    rf = data["rf_daily"].to_numpy(float)
    months = data.index.year * 12 + data.index.month
    month_start = np.empty(len(data), dtype=bool)
    month_start[0] = True
    month_start[1:] = months[1:] != months[:-1]
    return {
        "tr": tr,
        "rf": rf,
        "rf_annual": data["rf_annual"].to_numpy(float),
        "S": data["S"].to_numpy(float),
        "sigma": data["sigma"].to_numpy(float),
        "real_tr": data["real_tr"].to_numpy(bool),
        "month_start": month_start,
        "lev": levered_daily(tr, rf, cfg.leverage),
    }


def rolling_windows(
    data: pd.DataFrame,
    cfg: Config,
    window_years: int,
    step_months: int = 1,
    require_real_tr: bool = True,
) -> List[PathResult]:
    """Run every rolling window of `window_years`, stepping `step_months`.

    If require_real_tr, windows are restricted to the span where the genuine
    total-return index is available (so results aren't polluted by the
    dividend approximation).
    """
    arrays = build_arrays(data, cfg)
    dates = data.index
    n = len(dates)

    if require_real_tr and arrays["real_tr"].any():
        first_real = int(np.flatnonzero(arrays["real_tr"])[0])
    else:
        first_real = 0

    results: List[PathResult] = []
    start_i = first_real
    last_start_date = dates[-1] - pd.DateOffset(years=window_years)
    # Step by calendar months from the first eligible start.
    cur = dates[first_real]
    while cur <= last_start_date:
        start_i = int(dates.searchsorted(cur, side="left"))
        if start_i >= n:
            break
        target_end = dates[start_i] + pd.DateOffset(years=window_years)
        end_i = int(dates.searchsorted(target_end, side="left"))
        end_i = min(end_i, n - 1)
        if end_i > start_i:
            results.append(run_path(data, cfg, start_i, end_i, arrays))
        cur = cur + pd.DateOffset(months=step_months)
    return results
