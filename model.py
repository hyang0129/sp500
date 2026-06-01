"""Core financial model: Black-Scholes put pricing and the leverage engine.

The leverage engine implements the collateralized-futures constant-leverage
identity (handoff 3.1):

    r_levered = L * TR  -  (L - 1) * rf

applied per rebalance period. The single-path orchestration (rolls, premiums,
liquidation) lives in backtest.py; this module holds the reusable primitives.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


# ---------------------------------------------------------------------------
# Black-Scholes
# ---------------------------------------------------------------------------
def bs_put(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """European put price with continuous dividend yield q.

    P = K e^{-rT} N(-d2) - S e^{-qT} N(-d1)
    """
    if T <= 0 or sigma <= 0:
        return max(K * np.exp(-r * T) - S * np.exp(-q * T), 0.0)
    sqrtT = np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


def delta_strike(S: float, target_abs_delta: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Strike K of a European put with |delta| == target_abs_delta.

    put delta = -e^{-qT} N(-d1)  =>  N(-d1) = |delta| e^{qT}  =>  d1 = -Phi^{-1}(.)
    then invert d1 = (ln(S/K) + (r-q+sigma^2/2)T)/(sigma sqrt(T)) for K.
    """
    if sigma <= 0 or T <= 0:
        return S
    x = min(max(target_abs_delta * np.exp(q * T), 1e-6), 1.0 - 1e-6)
    d1 = -norm.ppf(x)
    return S * np.exp(-(d1 * sigma * np.sqrt(T)) + (r - q + 0.5 * sigma * sigma) * T)


def bs_call(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """European call price (provided for put-call-parity testing)."""
    if T <= 0 or sigma <= 0:
        return max(S * np.exp(-q * T) - K * np.exp(-r * T), 0.0)
    sqrtT = np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


# ---------------------------------------------------------------------------
# Leverage segment engine
# ---------------------------------------------------------------------------
def levered_daily(tr: np.ndarray, rf: np.ndarray, L: float) -> np.ndarray:
    """Per-day levered *simple* return: L*tr - (L-1)*rf (handoff 3.1)."""
    return L * tr - (L - 1.0) * rf


def segment_equity_path(
    E0: float,
    lev: np.ndarray,
    month_start: np.ndarray,
    rebalance: str,
) -> np.ndarray:
    """Equity path over one annual segment, starting from equity E0.

    `lev` is the array of daily levered simple returns for the days *after* the
    roll up to and including the next roll. `month_start[i]` marks days that
    begin a new monthly rebalance period.

    - rebalance == "daily": notional resets every day -> multiplicative
      compounding, equity_i = E0 * prod(1 + lev). Captures volatility decay.
    - rebalance == "monthly": notional is fixed within a month (futures
      contracts held), so within a month equity is *linear* in cumulative
      return off the month-start equity; equity compounds across months.

    Returns the equity level after each day (len == len(lev)). No liquidation
    is applied here; the caller scans the path for breaches.
    """
    n = len(lev)
    if n == 0:
        return np.empty(0)
    if rebalance == "daily":
        return E0 * np.cumprod(1.0 + lev)

    # monthly: walk month blocks, resetting the notional base each block.
    path = np.empty(n)
    E = E0
    starts = np.flatnonzero(month_start)
    # Ensure the segment's first day starts a block.
    if starts.size == 0 or starts[0] != 0:
        starts = np.insert(starts, 0, 0)
    bounds = list(starts) + [n]
    for a, b in zip(bounds[:-1], bounds[1:]):
        cum = np.cumsum(lev[a:b])
        block = E * (1.0 + cum)
        path[a:b] = block
        E = block[-1]
    return path
