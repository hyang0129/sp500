"""Futures contract specs and a collateralized-futures portfolio engine.

Modeling approach
-----------------
A futures account is fully collateralized: the cash balance earns the
short-term rate, and each futures position contributes its *excess* return on
notional. This is the same identity used by the leverage engine in `model.py`:

    d(equity) = equity * rf_daily  +  sum_i  notional_i * (asset_TR_i - rf_daily)

For Treasury note futures the "asset" is the cheapest-to-deliver (CTD) note.
We model it as a constant-maturity par note that is re-struck at each quarterly
roll (mimicking rolling into a new CTD), and we **fully reprice** the bond at
each new yield rather than using a linear DV01. That matters here: a linear
DV01 badly overstates losses when yields move 700+ bp, because duration itself
falls sharply as yields rise (convexity).

Contract specs (CME):
    MES  Micro E-mini S&P 500   $5 x index
    ZT   2-Year T-Note          $200,000 face, CTD ~2.0y
    ZN   10-Year T-Note         $100,000 face, CTD ~6.5y  (deliverable 6.5-10y)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np


# ---------------------------------------------------------------------------
# Contract specifications
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FutureSpec:
    name: str
    kind: str                 # "equity" or "bond"
    multiplier: float = 0.0   # equity: $ per index point
    face: float = 0.0         # bond: $ face value
    ctd_maturity: float = 0.0 # bond: CTD maturity in years
    yield_key: str = ""       # bond: which yield series drives it
    maint_margin: float = 0.0 # $ per contract (assumption, see README)


MES = FutureSpec("MES", "equity", multiplier=5.0, maint_margin=2400.0)
ZT = FutureSpec("ZT", "bond", face=200_000.0, ctd_maturity=2.0,
                yield_key="y2", maint_margin=1300.0)
ZN = FutureSpec("ZN", "bond", face=100_000.0, ctd_maturity=6.5,
                yield_key="y6_5", maint_margin=2200.0)

SPECS: Dict[str, FutureSpec] = {"MES": MES, "ZT": ZT, "ZN": ZN}


# ---------------------------------------------------------------------------
# Bond pricing
# ---------------------------------------------------------------------------
def n_coupons_left(maturity: float, freq: int = 2) -> int:
    """Number of coupons still to be paid on a bond with `maturity` years left."""
    if maturity <= 0:
        return 0
    return int(np.ceil(maturity * freq - 1e-9))


def bond_price(y: float, coupon: float, maturity: float, freq: int = 2) -> float:
    """*Dirty* price per 100 face of a semiannual coupon bond.

    This is the present value of all remaining cashflows, so it already
    includes accrued interest — do not add accrued on top of it when computing
    a holding-period return (see `BondLeg.step`).

    y, coupon are decimals (0.045 = 4.5%). `maturity` in years.
    """
    if maturity <= 0:
        return 100.0
    n_per = maturity * freq
    n_full = n_coupons_left(maturity, freq)
    frac = n_full - n_per  # fraction of a period already elapsed
    c = coupon * 100.0 / freq
    disc = 1.0 + y / freq
    # cashflow k (k=1..n_full) lands at (k - frac) periods from now
    k = np.arange(1, n_full + 1)
    t = k - frac
    pv = float(np.sum(c / disc**t) + 100.0 / disc**t[-1])
    return pv


def bond_duration(y: float, coupon: float, maturity: float, freq: int = 2) -> float:
    """Modified duration (years), by central difference — used for reporting."""
    h = 1e-4
    p_up = bond_price(y + h, coupon, maturity, freq)
    p_dn = bond_price(y - h, coupon, maturity, freq)
    p = bond_price(y, coupon, maturity, freq)
    return -(p_up - p_dn) / (2 * h) / p


def dv01(y: float, coupon: float, maturity: float, face: float, freq: int = 2) -> float:
    """Dollar value of 1bp for `face` of this bond."""
    h = 1e-4
    p_up = bond_price(y + h, coupon, maturity, freq)
    p_dn = bond_price(y - h, coupon, maturity, freq)
    return (p_dn - p_up) / 2.0 / 100.0 * face


# ---------------------------------------------------------------------------
# Position state
# ---------------------------------------------------------------------------
@dataclass
class BondLeg:
    """A rolled constant-maturity bond future position."""
    spec: FutureSpec
    contracts: float
    coupon: float = 0.0        # decimal, set at each roll
    maturity: float = 0.0      # years remaining on the CTD
    price: float = 100.0       # per 100 face

    def roll(self, y: float) -> None:
        """Re-strike as a fresh par note at the prevailing yield."""
        self.coupon = y
        self.maturity = self.spec.ctd_maturity
        self.price = 100.0

    def step(self, y_new: float, dt_years: float) -> tuple[float, float]:
        """Advance one period. Returns (total_return, notional_before).

        `bond_price` is a dirty price, so it already accretes coupon income as
        time passes; the only cash to add back is an actual coupon *payment*,
        which happens when the position crosses a coupon date (the dirty price
        drops by the coupon at that moment). Adding accrued interest on top of
        the dirty-price change would double-count the coupon.
        """
        notional = self.spec.face * self.price / 100.0
        n_before = n_coupons_left(self.maturity)
        self.maturity = max(self.maturity - dt_years, 1e-6)
        n_after = n_coupons_left(self.maturity)
        coupon_paid = (self.coupon * 100.0 / 2.0) * (n_before - n_after)
        p_new = bond_price(y_new, self.coupon, self.maturity)
        tr = (p_new - self.price + coupon_paid) / self.price
        self.price = p_new
        return tr, notional
