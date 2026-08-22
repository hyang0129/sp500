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
