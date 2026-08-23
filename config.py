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
    # Protect the full leveraged notional ("full" -> L*equity) or just the
    # 1x base ("base" -> equity). Full is the default; base is cheaper but
    # leaves the leverage exposed.
    protect_notional: str = "full"
    roll_period_years: float = 1.0  # annual roll (BS T)

    # --- option pricing ----------------------------------------------------
    # "fair"       -> use sigma as observed.
    # "marked_up"  -> sigma *= vrp_markup to reflect the volatility risk
    #                 premium (index puts trade richer than BS-fair).
    vrp_mode: str = "fair"
    vrp_markup: float = 1.2
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
    maintenance_frac: float = 0.0  # liquidate when equity <= maintenance_frac
    # Maintenance margin as a fraction of *exposure notional*. A broker
    # liquidates here, not at zero equity. MES is ~$2,400 on ~$38k notional
    # = 6.5%. Set 0.0 to disable and only liquidate at zero equity (the old,
    # unrealistically generous behaviour).
    maintenance_rate: float = 0.065
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
