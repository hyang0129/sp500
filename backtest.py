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
from model import bs_put, delta_strike, levered_daily, segment_equity_path


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
    # day-based so sub-annual tenors (e.g. 30-day ~ period_years=1/12) work too.
    period_days = max(1, int(round(period_years * 365.25)))
    while True:
        anniv = d0 + pd.Timedelta(days=k * period_days)
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

    div_yield = arrays["div_yield"]
    L = cfg.leverage
    m = cfg.put_moneyness
    protect_full = cfg.protect_notional == "full"
    put_sign = 1.0 if cfg.put_side == "buy" else -1.0  # +1 long hedge, -1 short
    ratio_cfg = cfg.put_ratio
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
    put_notional = 0.0
    put_open_i = -1

    for k in range(len(rolls)):
        i = rolls[k]
        final = k == len(rolls) - 1
        # 1) Close the put from the previous roll. At its natural expiry (every
        #    normal roll) this is a cash settlement at intrinsic. At the FINAL
        #    roll the window cuts the option's life short, so close it at MARKET
        #    value (intrinsic + remaining time value) and pay the spread -- not
        #    intrinsic, which would hand the writer an unearned time-value windfall.
        if put_units > 0.0 and not ruined:
            if final:
                elapsed = (dates[i] - dates[put_open_i]).days / 365.25
                remaining = max(T - elapsed, 0.0)
                if remaining > 1e-6:
                    base_sig = sigma[i] * (cfg.vrp_markup if cfg.vrp_mode == "marked_up" else 1.0)
                    eff_sigma = base_sig + cfg.skew_slope * max((S[i] - put_K) / S[i], 0.0)
                    settle_val = bs_put(S[i], put_K, remaining, rf_annual[i], eff_sigma, div_yield[i]) * put_units
                    equity -= cfg.spread_frac * settle_val  # spread paid to close early
                else:
                    settle_val = max(put_K - S[i], 0.0) * put_units
                equity += put_sign * settle_val
            else:
                payoff = max(put_K - S[i], 0.0) * put_units
                equity += put_sign * payoff
            if equity <= maint:
                ruined = True
                equity = 0.0
        put_units = 0.0
        if record_curve:
            curve_idx.append(i)
            curve_val.append(max(equity, 0.0))

        if k == len(rolls) - 1:
            break  # final roll: window ends, nothing more to do

        # 2) Open the put overlay for the coming period (premium now).
        #    Long: pay premium. Short: collect it.
        if (m is not None or cfg.put_delta is not None) and not ruined and equity > 0.0:
            Si = S[i]
            base_sig = sigma[i] * (cfg.vrp_markup if cfg.vrp_mode == "marked_up" else 1.0)
            if cfg.put_delta is not None:
                K = delta_strike(Si, abs(cfg.put_delta), T, rf_annual[i], base_sig, div_yield[i])
            else:
                K = (1.0 - m) * Si
            # add the volatility skew for OTM puts (higher IV the further OTM)
            eff_sigma = base_sig + cfg.skew_slope * max((Si - K) / Si, 0.0)
            ratio = ratio_cfg if ratio_cfg is not None else (L if protect_full else 1.0)
            notional = ratio * equity
            units = notional / Si
            price = bs_put(Si, K, T, rf_annual[i], eff_sigma, div_yield[i])
            equity -= put_sign * price * units
            # bid/ask: you transact worse than mid, so the spread always costs
            # you (less premium when selling, more when buying).
            equity -= cfg.spread_frac * price * units
            if equity <= maint:
                ruined = True
                equity = 0.0
            else:
                put_units = units
                put_K = K
                put_notional = notional
                put_open_i = i

        # 3) Run the leverage engine over the segment [i, rolls[k+1]].
        a, b = i + 1, rolls[k + 1] + 1  # daily returns from day after roll to next roll
        if ruined or a >= b:
            continue
        seg_lev = lev[a:b]
        seg_ms = month_start[a:b]
        path = segment_equity_path(equity, seg_lev, seg_ms, cfg.rebalance)

        # 4) Liquidation scan (absorbing zero) + drawdown tracking.
        # Mark the put's intrinsic value into the equity used for the margin
        # test: a LONG put is an asset (credited, opt-in via put_mtm flag); a
        # SHORT put is a liability (always debited once a margin model is on, so
        # a put-writer can actually be margin-called intra-period).
        short_put = put_sign < 0.0 and put_units > 0.0
        mark_short = short_put and cfg.maint_margin_frac > 0.0
        check_path = path
        if put_units > 0.0 and (cfg.put_mtm_for_liquidation or mark_short):
            intrinsic = np.maximum(put_K - S[a:b], 0.0) * put_units
            check_path = path + put_sign * intrinsic

        # Liquidation threshold per day: an absolute floor (maintenance_frac),
        # and -- if maint_margin_frac>0 -- a maintenance requirement of that
        # fraction of the period notional. The futures leg requires margin on
        # L*equity; a short put requires its own margin on the put notional
        # (its MTM loss is already netted out of check_path above).
        if cfg.maint_margin_frac > 0.0:
            period_start_eq = _period_start_equity(path, seg_ms, equity, cfg.rebalance)
            req = cfg.maint_margin_frac * L * period_start_eq
            if short_put:
                req = req + cfg.maint_margin_frac * put_notional
            thresh = np.maximum(maint, req)
        else:
            thresh = maint
        breach = np.flatnonzero(check_path <= thresh)
        if breach.size > 0 and daily_check:
            first = breach[0]
            path = path.copy()
            path[first:] = 0.0
            ruined = True
        elif breach.size > 0 and not daily_check:
            # month_end model: only liquidate if a *month-end* mark breaches.
            ms_idx = np.flatnonzero(seg_ms)
            month_ends = np.append(ms_idx[1:] - 1, len(path) - 1) if ms_idx.size else np.array([len(path) - 1])
            thr_me = thresh[month_ends] if np.ndim(thresh) else thresh
            bad = month_ends[check_path[month_ends] <= thr_me]
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


def _period_start_equity(path: np.ndarray, seg_ms: np.ndarray, entry_equity: float, rebalance: str) -> np.ndarray:
    """Equity at the start of each day's *rebalance period* (for margin calls).

    daily: the period is the day, so the base is the prior day's equity.
    monthly: the period is the month; every day in a month block shares the
    block-start equity (the notional was fixed there).
    """
    n = len(path)
    if rebalance == "daily":
        out = np.empty(n)
        out[0] = entry_equity
        out[1:] = path[:-1]
        return out
    out = np.empty(n)
    starts = np.flatnonzero(seg_ms)
    if starts.size == 0 or starts[0] != 0:
        starts = np.insert(starts, 0, 0)
    bounds = list(starts) + [n]
    for s, e in zip(bounds[:-1], bounds[1:]):
        out[s:e] = entry_equity if s == 0 else path[s - 1]
    return out


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
        "div_yield": data["div_yield"].to_numpy(float),
        "real_tr": data["real_tr"].to_numpy(bool),
        "has_rf": data["has_rf"].to_numpy(bool) if "has_rf" in data else np.ones(len(data), bool),
        "month_start": month_start,
        "lev": levered_daily(tr, rf, cfg.leverage),
    }


def rolling_windows(
    data: pd.DataFrame,
    cfg: Config,
    window_years: int,
    step_months: int = 1,
    require_real_tr: bool = True,
    history: str = "real_tr",
) -> List[PathResult]:
    """Run every rolling window of `window_years`, stepping `step_months`.

    `history` selects the eligible start span:
      "real_tr" (default): only where the genuine total-return index exists
        (1988+), so dividends are exact -- the conservative headline span.
      "rf": any window with a genuine financing rate (1934+); pre-1988 windows
        use the time-varying dividend-yield add-back. Use this to reach the
        1929-era / high-rate / Japan-style stress regimes the audit flagged.
      "all": the entire price history.
    `require_real_tr=False` is kept as a back-compat alias for history="all".
    """
    arrays = build_arrays(data, cfg)
    dates = data.index
    n = len(dates)

    if not require_real_tr:
        history = "all"
    if history == "real_tr" and arrays["real_tr"].any():
        first_real = int(np.flatnonzero(arrays["real_tr"])[0])
    elif history == "rf" and arrays["has_rf"].any():
        first_real = int(np.flatnonzero(arrays["has_rf"])[0])
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
