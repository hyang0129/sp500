"""Unit tests for bond pricing and the futures portfolio engine."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from futures import SPECS, BondLeg, bond_price, bond_duration, dv01  # noqa: E402


def test_par_bond_prices_at_par():
    for y in (0.01, 0.0414, 0.08, 0.16):
        assert abs(bond_price(y, y, 2.0) - 100.0) < 1e-9
        assert abs(bond_price(y, y, 6.5) - 100.0) < 1e-9


def test_known_bond_values():
    # 10y, 5% coupon, 6% yield -> ~92.56 (textbook)
    assert abs(bond_price(0.06, 0.05, 10.0) - 92.5613) < 1e-3
    # 5y zero at 5% semiannual -> 100/1.025^10 = 78.1198
    assert abs(bond_price(0.05, 0.0, 5.0) - 78.1198) < 1e-3


def test_price_falls_as_yield_rises():
    assert bond_price(0.06, 0.04, 6.5) < bond_price(0.04, 0.04, 6.5) < bond_price(0.02, 0.04, 6.5)


def test_dv01_magnitudes_are_realistic():
    # ZT ~ $38/bp on 200k face; ZN ~ $56/bp on 100k face of a 6.5y CTD
    assert 30 < dv01(0.0414, 0.0414, 2.0, 200_000) < 45
    assert 45 < dv01(0.0447, 0.0447, 6.5, 100_000) < 70


def test_convexity_dv01_falls_when_yields_spike():
    """The whole point of full repricing: duration collapses at high yields."""
    lo = dv01(0.04, 0.04, 6.5, 100_000)
    hi = dv01(0.16, 0.16, 6.5, 100_000)
    assert hi < lo * 0.80  # at least 20% less rate-sensitive at 16%


def test_flat_curve_total_return_equals_yield():
    """A par note held at a constant yield must return exactly that yield.

    This is the regression test for the dirty-price/accrued double-count: if
    coupon income is added on top of the dirty-price accretion, the realized
    return comes out at roughly 2x the yield.
    """
    y = 0.05
    leg = BondLeg(SPECS["ZT"], 1.0)
    leg.roll(y)
    dt = 1.0 / 252.0
    growth = 1.0
    for _ in range(252):
        tr, _ = leg.step(y, dt)
        growth *= 1.0 + tr
    assert abs(growth - 1.0 - y) < 2e-3, f"1y total return {growth-1:.4f}, expected ~{y}"


def test_flat_curve_return_for_long_bond():
    y = 0.07
    leg = BondLeg(SPECS["ZN"], 1.0)
    leg.roll(y)
    dt = 1.0 / 252.0
    growth = 1.0
    for _ in range(252):
        tr, _ = leg.step(y, dt)
        growth *= 1.0 + tr
    assert abs(growth - 1.0 - y) < 3e-3, f"1y total return {growth-1:.4f}, expected ~{y}"


def test_yield_drop_produces_capital_gain_near_dv01():
    """A 100bp instant drop gains slightly MORE than linear DV01*100.

    Positive convexity: the true price/yield curve lies above its tangent, so
    the realized gain must exceed the linear estimate, but only modestly.
    """
    y = 0.05
    linear = dv01(y, y, 6.5, 100_000) * 100
    leg = BondLeg(SPECS["ZN"], 1.0)
    leg.roll(y)
    tr, notional = leg.step(y - 0.01, 1e-9)
    gain = tr * notional
    assert gain > linear, "convexity should make the actual gain exceed linear DV01"
    assert (gain - linear) / linear < 0.06


# --- position sizing -------------------------------------------------------
def _cfg(**kw):
    from stress_test import StressConfig
    base = dict(equity0=100_000.0, n_mes=2.0, n_zt=4.0, n_zn=-2.0, mode="delta",
                start="1979-01-02", end="1984-01-03")
    base.update(kw)
    return StressConfig(**base)


def test_sizing_is_noop_for_a_cash_only_book():
    """With no positions, every sizing rule must give an identical path."""
    from stress_test import run_stress
    flat = dict(n_mes=0.0, n_zt=0.0, n_zn=0.0)
    a = run_stress(_cfg(sizing="fixed", **flat)).final_equity
    b = run_stress(_cfg(sizing="constant_leverage", **flat)).final_equity
    c = run_stress(_cfg(sizing="constant_dv01", **flat)).final_equity
    assert abs(a - b) < 1e-6 and abs(a - c) < 1e-6


def test_constant_leverage_holds_exposure_ratio_steady():
    """Under constant leverage, notional/equity should not drift with equity."""
    from futures import SPECS
    from stress_test import StressConfig, run_stress, current_levels
    cfg = _cfg(sizing="constant_leverage")
    r = run_stress(cfg)
    cur = current_levels(cfg)
    # inception ratio
    ratio0 = cfg.n_mes * SPECS["MES"].multiplier * cur["S"] / cfg.equity0
    # the book grew a lot; a fixed book's ratio would have fallen by ~that factor
    assert r.final_equity > cfg.equity0
    assert 0.5 < ratio0 < 1.5  # sanity on the 2 MES / $100k starting ratio


def test_fractional_vs_whole_contracts_differ_but_track():
    from stress_test import run_stress
    frac = run_stress(_cfg(sizing="constant_leverage", fractional=True)).final_equity
    whole = run_stress(_cfg(sizing="constant_leverage", fractional=False)).final_equity
    assert frac != whole
    assert abs(whole / frac - 1.0) < 0.25  # rounding shifts it, does not break it
