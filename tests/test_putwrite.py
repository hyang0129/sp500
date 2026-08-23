"""Tests for the short-put (put-writing) module."""
import os
import sys

import numpy as np
from scipy.stats import norm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import bs_put  # noqa: E402
from putwrite import PWConfig, put_margin, run_putwrite, strike_from_delta, load  # noqa: E402


def _put_delta(S, K, T, r, sigma, q):
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return -np.exp(-q * T) * norm.cdf(-d1)


def test_strike_from_delta_round_trips():
    for sigma in (0.12, 0.20, 0.35, 0.60):
        for d in (0.05, 0.10, 0.20):
            K = strike_from_delta(100, d, 1 / 12, 0.04, sigma, 0.018)
            assert abs(abs(_put_delta(100, K, 1 / 12, 0.04, sigma, 0.018)) - d) < 1e-6


def test_higher_vol_pushes_same_delta_further_otm():
    lo = strike_from_delta(100, 0.10, 1 / 12, 0.04, 0.12, 0.018)
    hi = strike_from_delta(100, 0.10, 1 / 12, 0.04, 0.35, 0.018)
    assert hi < lo


def test_higher_delta_collects_more_premium():
    prem = []
    for d in (0.05, 0.10, 0.20):
        K = strike_from_delta(100, d, 1 / 12, 0.04, 0.20, 0.018)
        prem.append(bs_put(100, K, 1 / 12, 0.04, 0.20, 0.018))
    assert prem[0] < prem[1] < prem[2]


def test_two_month_premium_exceeds_one_month_at_same_delta():
    k1 = strike_from_delta(100, 0.10, 1 / 12, 0.04, 0.20, 0.018)
    k2 = strike_from_delta(100, 0.10, 2 / 12, 0.04, 0.20, 0.018)
    assert bs_put(100, k2, 2 / 12, 0.04, 0.20, 0.018) > bs_put(100, k1, 1 / 12, 0.04, 0.20, 0.018)


def test_margin_is_positive_and_grows_as_strike_approaches_spot():
    m_far = put_margin(100, 90, 1.0, 0.3)
    m_near = put_margin(100, 98, 1.0, 0.9)
    assert 0 < m_far < m_near


def test_zero_weight_reproduces_cash_only():
    """w=0 must be exactly the collateral earning the bill rate."""
    d = load()
    a = run_putwrite(d, PWConfig(weight=0.0, core_leverage=0.0))
    b = run_putwrite(d, PWConfig(weight=0.0, delta=0.20, structure="roll", core_leverage=0.0))
    assert abs(a.final - b.final) < 1e-12
    assert a.n_expiries == 0
    # Not exactly zero: ^IRX printed slightly negative in 2015 and 2020, so
    # cash collateral really did tick down a hair.
    assert a.max_drawdown < 1e-3


def test_selling_puts_adds_return_over_cash():
    d = load()
    cash = run_putwrite(d, PWConfig(weight=0.0))
    sold = run_putwrite(d, PWConfig(weight=1.0, delta=0.20, structure="hold"))
    assert sold.cagr > cash.cagr
    assert sold.premium_collected > sold.payouts  # the VRP is real in-sample


def test_hold_to_expiry_beats_closing_early():
    """Theta accelerates into expiry, so capturing the final month wins."""
    d = load()
    hold = run_putwrite(d, PWConfig(weight=1.0, delta=0.10, structure="hold"))
    roll = run_putwrite(d, PWConfig(weight=1.0, delta=0.10, structure="roll"))
    assert hold.cagr > roll.cagr


# --- volatility smile ------------------------------------------------------
def test_smile_slope_sign_and_magnitude():
    from putwrite import smile_slope
    # SKEW = 100 means lognormal: no skew
    assert abs(smile_slope(100.0, 1 / 12)) < 1e-12
    # higher SKEW = steeper, and always a positive slope (IV rises as K falls)
    assert 0 < smile_slope(110.0, 1 / 12) < smile_slope(140.0, 1 / 12)


def test_iv_rises_as_strike_falls():
    from putwrite import iv_at_strike, smile_slope
    sl = smile_slope(119.8, 1 / 12)
    assert iv_at_strike(100, 90, 0.15, sl) > iv_at_strike(100, 95, 0.15, sl) > 0.15
    # upside strikes are not marked up by this downside-only smile
    assert iv_at_strike(100, 105, 0.15, sl) == 0.15


def test_strike_from_delta_smile_is_further_otm_than_flat():
    """A steeper smile means the same delta sits at a lower strike."""
    from putwrite import smile_slope, strike_from_delta, strike_from_delta_smile
    flat = strike_from_delta(100, 0.10, 1 / 12, 0.04, 0.15, 0.018)
    K, iv = strike_from_delta_smile(100, 0.10, 1 / 12, 0.04, 0.15,
                                    smile_slope(119.8, 1 / 12), 0.018)
    assert K < flat and iv > 0.15


def test_skew_model_pays_more_for_far_otm_than_flat_vix():
    """The whole point: flat-VIX underprices the tail a seller is paid for."""
    d = load()
    flat = run_putwrite(d, PWConfig(weight=1.0, delta=0.05, structure="hold"))
    skew = run_putwrite(d, PWConfig(weight=1.0, delta=0.05, structure="hold",
                                    vol_model="skew", atm_offset=0.03))
    assert skew.premium_collected > flat.premium_collected
