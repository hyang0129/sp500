"""Configuration for the leveraged S&P 500 tail-protection backtest.

Every modeling knob from the research handoff lives here with the documented
default. A single `Config` instance fully determines one experiment "cell".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    # --- leverage & rebalancing -------------------------------------------
    leverage: float = 1.0
    # "monthly" matches a check-finances-monthly cadence (primary);
    # "daily" captures leveraged-ETF-style volatility decay (comparison).
    rebalance: str = "monthly"

    # --- put-protection overlay -------------------------------------------
    # Out-of-the-money fraction for the annually-rolled protective put.
    # None  -> no protection. 0.20 -> strike 20% below spot.
    put_moneyness: Optional[float] = None
    # Target |delta| for the put strike instead of a fixed moneyness (e.g. 0.25
    # sells the 25-delta put -- a vol-adaptive strike). Overrides put_moneyness
    # for strike selection when set.
    put_delta: Optional[float] = None
    # Optional long protective WING (a further-OTM put bought against the short
    # leg, same quantity) -> a defined-risk short put SPREAD. Specify by delta
    # (must be < put_delta, i.e. further OTM) or by moneyness (> put_moneyness).
    wing_delta: Optional[float] = None
    wing_moneyness: Optional[float] = None
    # Linear vol skew (points of vol per unit OTM fraction) added to the pricing
    # sigma for OTM puts: eff_sigma = base + skew_slope*max((S-K)/S, 0). 0.0 =
    # flat (no skew). ~0.6-0.8 approximates 1-month SPX put skew.
    skew_slope: float = 0.0
    # "buy"  -> long protective puts (premium paid, payoff received: a hedge).
    # "sell" -> short puts (premium collected, payoff paid: income / VRP harvest,
    #           a short-vol overlay that fattens the left tail).
    put_side: str = "buy"
    # Put notional as a fraction of equity. None -> fall back to protect_notional
    # ("full"->L*equity, "base"->equity). E.g. put_ratio=0.5 sells/buys puts on
    # 50% of the portfolio's notional.
    put_ratio: Optional[float] = None
    # Protect the full leveraged notional ("full" -> L*equity) or just the
    # 1x base ("base" -> equity). Full is the default; base is cheaper but
    # leaves the leverage exposed.
    protect_notional: str = "full"
    roll_period_years: float = 1.0  # roll/expiry tenor in years (1/12 ~= 30-day)

    # --- option pricing ----------------------------------------------------
    # "fair"       -> use sigma as observed.
    # "marked_up"  -> sigma *= vrp_markup to reflect the volatility risk
    #                 premium (index puts trade richer than BS-fair).
    vrp_mode: str = "fair"
    vrp_markup: float = 1.2
    # Execution cost as a fraction of premium (the bid/ask half-spread you give
    # up): you always transact worse than mid, so this is subtracted from the
    # premium received (selling) or added to the premium paid (buying). 0.0 =
    # trade at mid (the idealized assumption). ~0.02-0.05 is realistic for
    # liquid 1-month index options; retail/illiquid is worse.
    spread_frac: float = 0.0
    # Where the pricing vol comes from: "vix" (preferred, /100) with fallback
    # to trailing realized vol when VIX is unavailable; or "realized" always.
    vol_source: str = "vix"
    realized_vol_window: int = 60  # trading days

    # --- liquidation / ruin ------------------------------------------------
    # "daily_path" (default, realistic): step daily to detect intra-period
    #   breaches even when rebalancing monthly.
    # "month_end": float exposure intra-month, only mark at month end
    #   (understates ruin at 3x; comparison only).
    liquidation_model: str = "daily_path"
    maintenance_frac: float = 0.0  # absolute equity floor: liquidate when equity <= this
    # Realistic margin call: liquidate when equity falls below this fraction of
    # the *period notional* (L * equity-at-period-start). 0.0 disables it (the
    # original literal-zero-ruin model). A typical broker maintenance margin on
    # index exposure is ~0.10-0.30; with this on, a 3x book is wiped by a deep
    # drawdown (not only by literal-zero equity), which is the realistic case.
    maint_margin_frac: float = 0.0
    # If True, credit the protective put's *intrinsic* value to equity when
    # testing for intra-period liquidation (a cheap mark-to-market proxy).
    # Default False matches the handoff's European "payoff only at roll" model.
    put_mtm_for_liquidation: bool = False

    # --- index / dividends -------------------------------------------------
    use_total_return: bool = True  # use ^SP500TR when available
    div_yield: float = 0.018  # annual; used for BS q and price->TR add-back

    # --- data --------------------------------------------------------------
    data_path: str = "data/sp500_daily.csv"
    trading_days_per_year: int = 252

    def label(self) -> str:
        prot = "none" if self.put_moneyness is None else f"put{int(self.put_moneyness*100)}"
        return f"L{self.leverage:g}_{prot}_{self.rebalance}_{self.vrp_mode}"
