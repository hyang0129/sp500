"""Systematic put *selling* on the S&P — the other side of the protection trade.

The earlier study bought protective puts and paid the volatility risk premium.
This sells it. Two structures:

    "hold"   write a 1-month put, hold to expiry, settle intrinsic
    "roll"   write a 2-month put, buy it back after 1 month at its BS value

Strikes are set by target delta (5 / 10 / 20 delta), not fixed moneyness, so the
distance from spot widens automatically when vol is high — which is how these
are actually traded.

Sizing: short-put notional is `w * equity`, w in {0, 0.25, 0.5, 0.75, 1.0}.
Optionally layered on a long core of `L * equity` (monthly reset).

IMPORTANT — where the edge comes from. Options are priced off VIX, which
embeds the volatility risk premium (VIX systematically exceeds subsequent
realised vol). Selling at VIX and settling against the realised path therefore
captures the real, historical VRP rather than an assumed one. That is only
honest where VIX exists, so the study runs 1990-2026. October 1987 is handled
separately as an explicit stress scenario, since no implied-vol quote exists.

Margin: naked short index puts are margined roughly as
    max(20% * S - OTM_amount, 10% * K) * units + premium
per the standard Reg-T/CBOE rule. The account is liquidated if equity falls
below the requirement — that, not the intrinsic loss, is what actually ends a
put-writing account in a crash.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import norm

from config import Config
from data import prepare
from model import bs_put

TRADING_DAYS = 252


# ---------------------------------------------------------------------------
def strike_from_delta(S: float, target_delta: float, T: float, r: float,
                      sigma: float, q: float = 0.0) -> float:
    """Strike of a put with |delta| = target_delta.

    delta_put = -exp(-qT) * N(-d1)  =>  N(-d1) = |delta| * exp(qT)
    d1 = (ln(S/K) + (r - q + sigma^2/2)T) / (sigma sqrt(T))
    """
    if sigma <= 0 or T <= 0:
        return S
    p = min(max(target_delta * np.exp(q * T), 1e-6), 1 - 1e-6)
    d1 = -norm.ppf(p)
    return float(S * np.exp((r - q + 0.5 * sigma * sigma) * T - d1 * sigma * np.sqrt(T)))


def put_margin(S: float, K: float, units: float, premium: float) -> float:
    """Reg-T / CBOE naked short put maintenance requirement (dollars)."""
    otm = max(S - K, 0.0)
    a = 0.20 * S - otm
    b = 0.10 * K
    return (max(a, b) * units) + premium


def smile_slope(skew_index: float, T: float, damp: float = 1.0) -> float:
    """dIV/d(ln K/F) implied by the CBOE SKEW index.

    SKEW = 100 - 10*g1 with g1 the risk-neutral skewness of the 30-day log
    return. Backus-Foresi-Wu give, to first order,
        IV(d) ~ sigma * [1 - (g1/6) d],   d = ln(K/F)/(sigma sqrt(T))
    hence  dIV/d(ln K/F) = -g1 / (6 sqrt(T)).
    Returns a POSITIVE number: implied vol rises as the strike falls.

    This is a first-order expansion and overshoots badly at extreme SKEW
    (SKEW 183 implies +41 vol points at 5-delta, which is not a real market),
    so `damp` scales it and the caller should cap the result.
    """
    g1 = (100.0 - skew_index) / 10.0
    return damp * (-g1) / (6.0 * np.sqrt(T))


def iv_at_strike(S: float, K: float, atm_iv: float, slope: float,
                 cap: float = 0.60) -> float:
    """Implied vol for a downside strike under a linear-in-log-moneyness smile."""
    m = np.log(K / S)
    iv = atm_iv + slope * max(-m, 0.0)
    return float(min(max(iv, 1e-4), cap))


def strike_from_delta_smile(S: float, target_delta: float, T: float, r: float,
                            atm_iv: float, slope: float, q: float = 0.0,
                            iters: int = 40) -> tuple[float, float]:
    """Strike (and its IV) for a given |delta| when IV depends on the strike.

    Delta and IV are mutually dependent, so iterate to a fixed point.
    """
    iv = atm_iv
    K = S
    for _ in range(iters):
        K_new = strike_from_delta(S, target_delta, T, r, iv, q)
        iv_new = iv_at_strike(S, K_new, atm_iv, slope)
        if abs(K_new - K) < 1e-8 and abs(iv_new - iv) < 1e-10:
            K, iv = K_new, iv_new
            break
        K, iv = K_new, iv_new
    return K, iv


@dataclass
class PWConfig:
    weight: float = 0.5            # short-put notional as a multiple of equity
    delta: float = 0.10            # target |delta| (0.05 / 0.10 / 0.20)
    structure: str = "hold"        # "hold" (1M to expiry) | "roll" (2M, close at 1M)
    core_leverage: float = 0.0     # long S&P core, monthly reset (0 = cash + puts)
    div_yield: float = 0.018
    margin_mult: float = 1.0
    # --- volatility surface ---------------------------------------------
    # "flat_vix"  price every strike at VIX (ignores the smile; overstates ATM
    #             premium because VIX sits above ATM IV, understates far OTM)
    # "skew"      ATM IV = VIX - atm_offset, then add a SKEW-driven smile
    vol_model: str = "flat_vix"
    atm_offset: float = 0.0      # vol points (decimal) VIX sits above ATM IV
    skew_damp: float = 1.0       # damping on the Backus-Foresi-Wu slope
    start: str = "1990-01-02"
    end: str = "2026-08-14"


@dataclass
class PWResult:
    final: float
    cagr: Optional[float]
    max_drawdown: float
    ruined: bool
    n_expiries: int
    n_itm: int                     # expiries that finished in the money
    worst_month: float
    premium_collected: float
    payouts: float
    curve: pd.Series = None


# ---------------------------------------------------------------------------
def run_putwrite(data: pd.DataFrame, cfg: PWConfig) -> PWResult:
    win = data.loc[cfg.start:cfg.end]
    dates = win.index
    n = len(dates)
    if n < 60:
        raise ValueError(f"window too short: {n} rows")

    S = win["S"].to_numpy(float)
    sig = win["sigma"].to_numpy(float)
    skew = (win["skew"].to_numpy(float) if "skew" in win
            else np.full(len(win), 119.8))   # median SKEW if unavailable
    rf_a = win["rf_annual"].to_numpy(float)
    tr = win["tr"].to_numpy(float)
    months = dates.year * 12 + dates.month
    is_month_start = np.empty(n, dtype=bool)
    is_month_start[0] = True
    is_month_start[1:] = months[1:] != months[:-1]

    T_write = (2.0 if cfg.structure == "roll" else 1.0) / 12.0
    T_close = 1.0 / 12.0            # time remaining when we close a "roll" trade

    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    ruined = False
    q = cfg.div_yield
    L = cfg.core_leverage

    open_pos = None   # dict(K, units, premium, expiry_T_left)
    curve = np.empty(n)
    curve[0] = equity
    n_exp = n_itm = 0
    prem_total = payout_total = 0.0
    core_base = equity              # equity at last monthly core reset
    month_start_equity = equity

    for i in range(1, n):
        dt = (dates[i] - dates[i - 1]).days / 365.25
        rf_p = rf_a[i - 1] * dt

        # cash collateral + levered core (monthly reset, fixed notional in month)
        pnl = equity * rf_p
        if L > 0 and not ruined:
            pnl += L * core_base * (tr[i] + q * dt - rf_p)
        equity += pnl

        if is_month_start[i] and not ruined:
            # 1) settle / close the existing short put
            if open_pos is not None:
                K, units, prem = open_pos["K"], open_pos["units"], open_pos["prem"]
                if cfg.structure == "hold":
                    cost = max(K - S[i], 0.0) * units          # settle intrinsic
                else:
                    iv_c = sig[i]
                    if cfg.vol_model == "skew":
                        atm = max(sig[i] - cfg.atm_offset, 0.02)
                        iv_c = iv_at_strike(S[i], K, atm,
                                            smile_slope(skew[i], T_close, cfg.skew_damp))
                    cost = bs_put(S[i], K, T_close, rf_a[i], iv_c, q) * units
                equity -= cost
                payout_total += cost
                n_exp += 1
                if cost > 0 and (cfg.structure == "hold") and S[i] < K:
                    n_itm += 1
                elif cfg.structure == "roll" and S[i] < K:
                    n_itm += 1
                open_pos = None

            if equity <= 0:
                ruined, equity = True, 0.0

            # 2) write a new one
            if not ruined and cfg.weight > 0:
                if cfg.vol_model == "skew":
                    atm = max(sig[i] - cfg.atm_offset, 0.02)
                    sl = smile_slope(skew[i], T_write, cfg.skew_damp)
                    K, iv_w = strike_from_delta_smile(S[i], cfg.delta, T_write,
                                                      rf_a[i], atm, sl, q)
                else:
                    K = strike_from_delta(S[i], cfg.delta, T_write, rf_a[i], sig[i], q)
                    iv_w = sig[i]
                units = cfg.weight * equity / S[i]
                prem = bs_put(S[i], K, T_write, rf_a[i], iv_w, q) * units
                equity += prem
                prem_total += prem
                open_pos = dict(K=K, units=units, prem=prem, written=dates[i])

            core_base = equity
            month_start_equity = equity

        # --- mark to market: equity net of the open short put's value --------
        # `equity` above already banked the premium, so the liability is the
        # option's *current* value. Time to expiry decays day by day; for the
        # "roll" structure the trade is closed with T_close still left, so the
        # liability never decays past that.
        mtm = equity
        if open_pos is not None and not ruined:
            held = (dates[i] - open_pos["written"]).days / 365.25
            t_left = max(T_write - held, T_close if cfg.structure == "roll" else 1e-4)
            iv_m = sig[i]
            if cfg.vol_model == "skew":
                atm = max(sig[i] - cfg.atm_offset, 0.02)
                iv_m = iv_at_strike(S[i], open_pos["K"], atm,
                                    smile_slope(skew[i], max(t_left, 1e-3), cfg.skew_damp))
            mv = bs_put(S[i], open_pos["K"], t_left, rf_a[i], iv_m, q) * open_pos["units"]
            mtm = equity - mv
            req = cfg.margin_mult * put_margin(S[i], open_pos["K"],
                                               open_pos["units"], mv)
            if mtm < req:
                ruined = True
                equity = max(mtm, 0.0)

        if mtm <= 0:
            ruined, equity = True, 0.0

        curve[i] = max(mtm, 0.0)
        peak = max(peak, curve[i])
        max_dd = max(max_dd, 1.0 - curve[i] / peak)
        if ruined:
            curve[i:] = 0.0 if equity <= 0 else curve[i]
            break

    final = float(curve[-1])
    years = (dates[-1] - dates[0]).days / 365.25
    cagr = None if final <= 0 else final ** (1 / years) - 1
    mser = pd.Series(curve, index=dates)
    worst = mser.resample("ME").last().pct_change().min()
    return PWResult(final=final, cagr=cagr, max_drawdown=max_dd, ruined=ruined,
                    n_expiries=n_exp, n_itm=n_itm,
                    worst_month=float(worst) if pd.notna(worst) else 0.0,
                    premium_collected=prem_total, payouts=payout_total, curve=mser)


def load(cfg: Config | None = None, skew_path: str = "data/skew_daily.csv") -> pd.DataFrame:
    """Analysis panel, with the CBOE SKEW index merged in where available."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        d = prepare(cfg or Config())
    try:
        sk = pd.read_csv(skew_path, parse_dates=["date"]).set_index("date")
        d = d.join(sk[["skew"]], how="left")
        d["skew"] = d["skew"].ffill().fillna(119.8)
    except FileNotFoundError:
        d["skew"] = 119.8
    return d
