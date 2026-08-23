"""Volcker-era stress test of a leveraged futures portfolio.

Replays the *deltas* (daily changes) of the 1979-1989 Volcker inflation cycle
onto a portfolio held at today's market levels:

    long 1 (or 2) MES   +  long 2 ZT  +  short 1 ZN     on an $80,000 account

Two replay modes:
  "delta"  (default, matches the request): today's starting yields/index, then
           apply the historical *changes* day by day. Rates are floored at 0.
  "level"  (sensitivity): replay the actual historical yield levels, so the
           account earns the real 8-16% Volcker cash rates.

The distinction matters enormously: in "level" mode the collateral earns
double-digit interest for a decade, which dominates everything else.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from futures import SPECS, BondLeg, bond_duration, bond_price, dv01

TRADING_DAYS = 252


@dataclass
class StressConfig:
    equity0: float = 80_000.0
    n_mes: float = 1.0
    n_zt: float = 2.0
    n_zn: float = -1.0
    start: str = "1979-08-06"     # Volcker sworn in as Fed chair
    years: float = 10
    end: Optional[str] = None     # explicit end date; overrides `years`
    mode: str = "delta"           # "delta" | "level"
    div_yield: float = 0.045      # S&P dividend yield in that era (~4.5%)
    roll_months: int = 3          # quarterly futures roll

    # --- position sizing ---------------------------------------------------
    # "fixed"              hold the stated contract counts for the whole window
    #                      (risk falls as equity grows, rises as it shrinks)
    # "constant_leverage"  resize so each leg's NOTIONAL/equity stays at its
    #                      inception ratio  (the honest constant-risk book)
    # "constant_dv01"      resize the rates legs so DV01/equity stays constant;
    #                      differs from notional-matching because DV01 per
    #                      contract falls as yields rise (convexity)
    sizing: str = "fixed"
    resize_months: int = 1        # how often positions are resized
    fractional: bool = True       # allow fractional contracts
    min_contract: float = 0.0     # round positions to this increment if > 0
    rate_floor: float = 0.0005    # floor rates at 5bp in delta mode
    margin_mult: float = 1.0      # stress multiplier on maintenance margin
    equity_path: str = "data/sp500_daily.csv"
    rates_path: str = "data/treasury_yields_daily.csv"


@dataclass
class StressResult:
    label: str
    final_equity: float
    peak_equity: float
    min_equity: float
    max_drawdown: float
    cagr: Optional[float]
    ruined: bool
    margin_breach: Optional[pd.Timestamp]
    curve: pd.Series = field(repr=False, default=None)
    attrib: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
def load_panel(cfg: StressConfig) -> pd.DataFrame:
    """Daily panel over the stress window: equity index, bill rate, CTD yields."""
    eq = pd.read_csv(cfg.equity_path, parse_dates=["date"]).set_index("date")
    rt = pd.read_csv(cfg.rates_path, parse_dates=["date"]).set_index("date")
    rt["y6_5"] = rt["y6"] + (rt["y7"] - rt["y6"]) * 0.5  # ZN CTD ~6.5y

    df = pd.DataFrame(index=eq.index)
    df["S"] = eq["close"]
    df["bill"] = eq["rf_annual"]
    df = df.join(rt[["y2", "y10", "y6_5"]] / 100.0, how="inner").ffill().dropna()

    t0 = pd.Timestamp(cfg.start)
    t1 = pd.Timestamp(cfg.end) if cfg.end else t0 + pd.DateOffset(days=round(365.25 * cfg.years))
    win = df.loc[t0:t1]
    if len(win) < 20:
        raise ValueError(f"Not enough data in {t0.date()}..{t1.date()} ({len(win)} rows)")
    return win


def current_levels(cfg: StressConfig) -> dict:
    """Latest observed market levels — the portfolio's starting point."""
    eq = pd.read_csv(cfg.equity_path, parse_dates=["date"]).set_index("date")
    rt = pd.read_csv(cfg.rates_path, parse_dates=["date"]).set_index("date")
    rt["y6_5"] = rt["y6"] + (rt["y7"] - rt["y6"]) * 0.5
    e, r = eq.dropna(subset=["close"]).iloc[-1], rt.iloc[-1]
    return dict(
        asof_equity=eq.index[-1], asof_rates=rt.index[-1],
        S=float(e["close"]), bill=float(e["rf_annual"]),
        y2=float(r["y2"]) / 100.0, y10=float(r["y10"]) / 100.0,
        y6_5=float(r["y6_5"]) / 100.0,
    )


def run_stress(cfg: StressConfig, verbose: bool = False) -> StressResult:
    win = load_panel(cfg)
    cur = current_levels(cfg)
    dates = win.index
    n = len(dates)

    # --- build the replayed driver paths ---------------------------------
    if cfg.mode == "delta":
        # today's level + historical change since the window start
        y2 = cur["y2"] + (win["y2"].to_numpy() - win["y2"].iloc[0])
        y65 = cur["y6_5"] + (win["y6_5"].to_numpy() - win["y6_5"].iloc[0])
        y10 = cur["y10"] + (win["y10"].to_numpy() - win["y10"].iloc[0])
        bill = cur["bill"] + (win["bill"].to_numpy() - win["bill"].iloc[0])
        y2 = np.maximum(y2, cfg.rate_floor)
        y65 = np.maximum(y65, cfg.rate_floor)
        y10 = np.maximum(y10, cfg.rate_floor)
        bill = np.maximum(bill, cfg.rate_floor)
    elif cfg.mode == "level":
        y2, y65 = win["y2"].to_numpy(), win["y6_5"].to_numpy()
        y10, bill = win["y10"].to_numpy(), win["bill"].to_numpy()
    else:
        raise ValueError(f"unknown mode {cfg.mode}")

    # equity index: historical *returns* applied to today's level
    px_ret = win["S"].pct_change().fillna(0.0).to_numpy()
    # dividends accrue on the same calendar day-count as financing, so that
    # (equity TR - rf) is a like-for-like excess return.
    dt_all = np.diff(dates.to_numpy()).astype("timedelta64[D]").astype(float) / 365.25
    dt_all = np.insert(dt_all, 0, 0.0)
    eq_tr = px_ret + cfg.div_yield * dt_all
    S = cur["S"] * np.cumprod(1.0 + px_ret)

    # --- positions --------------------------------------------------------
    zt = BondLeg(SPECS["ZT"], cfg.n_zt)
    zn = BondLeg(SPECS["ZN"], cfg.n_zn)
    zt.roll(y2[0])
    zn.roll(y65[0])

    # Inception exposure ratios, used to resize under non-fixed sizing.
    mes_ratio = cfg.n_mes * SPECS["MES"].multiplier * S[0] / cfg.equity0
    zt_face_ratio = cfg.n_zt * SPECS["ZT"].face / cfg.equity0
    zn_face_ratio = cfg.n_zn * SPECS["ZN"].face / cfg.equity0
    zt_dv01_ratio = cfg.n_zt * dv01(y2[0], y2[0], 2.0, SPECS["ZT"].face) / cfg.equity0
    zn_dv01_ratio = cfg.n_zn * dv01(y65[0], y65[0], 6.5, SPECS["ZN"].face) / cfg.equity0

    def _round(x: float) -> float:
        if cfg.fractional and cfg.min_contract <= 0:
            return x
        step = cfg.min_contract if cfg.min_contract > 0 else 1.0
        return float(np.round(x / step) * step)

    def sized(equity_now: float, i: int) -> tuple[float, float, float]:
        """Contract counts for the current equity under the chosen sizing rule."""
        if cfg.sizing == "fixed":
            return cfg.n_mes, cfg.n_zt, cfg.n_zn
        e = max(equity_now, 0.0)
        n_mes_t = mes_ratio * e / (SPECS["MES"].multiplier * S[i])
        if cfg.sizing == "constant_leverage":
            n_zt_t = zt_face_ratio * e / SPECS["ZT"].face
            n_zn_t = zn_face_ratio * e / SPECS["ZN"].face
        elif cfg.sizing == "constant_dv01":
            d_zt = dv01(y2[i], y2[i], 2.0, SPECS["ZT"].face)
            d_zn = dv01(y65[i], y65[i], 6.5, SPECS["ZN"].face)
            n_zt_t = zt_dv01_ratio * e / max(d_zt, 1e-9)
            n_zn_t = zn_dv01_ratio * e / max(d_zn, 1e-9)
        else:
            raise ValueError(f"unknown sizing {cfg.sizing}")
        return _round(n_mes_t), _round(n_zt_t), _round(n_zn_t)

    n_mes_t, n_zt_t, n_zn_t = sized(cfg.equity0, 0)

    def margin_for(a: float, b: float, c: float) -> float:
        return cfg.margin_mult * (
            abs(a) * SPECS["MES"].maint_margin
            + abs(b) * SPECS["ZT"].maint_margin
            + abs(c) * SPECS["ZN"].maint_margin
        )

    margin_req = margin_for(n_mes_t, n_zt_t, n_zn_t)

    equity = cfg.equity0
    curve = np.empty(n)
    curve[0] = equity
    peak = equity
    max_dd = 0.0
    ruined = False
    breach: Optional[pd.Timestamp] = None
    closed = False  # positions closed after a margin breach
    attrib = {"cash": 0.0, "MES": 0.0, "ZT": 0.0, "ZN": 0.0}

    months = dates.year * 12 + dates.month
    for i in range(1, n):
        dt = (dates[i] - dates[i - 1]).days / 365.25
        rf_p = bill[i - 1] * dt

        cash_pnl = equity * rf_p
        pnl = cash_pnl
        attrib["cash"] += cash_pnl

        if not closed:
            # quarterly roll: re-strike both bond legs at prevailing yields
            if (months[i] != months[i - 1]) and (months[i] % cfg.roll_months == 0):
                zt.roll(y2[i - 1])
                zn.roll(y65[i - 1])

            # resize the book to the target exposure ratios (non-fixed sizing)
            if cfg.sizing != "fixed" and months[i] != months[i - 1] \
                    and (months[i] % cfg.resize_months == 0):
                n_mes_t, n_zt_t, n_zn_t = sized(equity, i - 1)
                margin_req = margin_for(n_mes_t, n_zt_t, n_zn_t)

            tr_zt, notl_zt = zt.step(y2[i], dt)
            tr_zn, notl_zn = zn.step(y65[i], dt)
            p_zt = n_zt_t * notl_zt * (tr_zt - rf_p)
            p_zn = n_zn_t * notl_zn * (tr_zn - rf_p)

            notl_mes = n_mes_t * SPECS["MES"].multiplier * S[i - 1]
            p_mes = notl_mes * (eq_tr[i] - rf_p)

            pnl += p_zt + p_zn + p_mes
            attrib["ZT"] += p_zt
            attrib["ZN"] += p_zn
            attrib["MES"] += p_mes

        equity += pnl
        if equity <= 0:
            equity = 0.0
            ruined = True
            closed = True
        elif (not closed) and equity < margin_req:
            breach = dates[i]
            closed = True  # forced to flatten; remainder sits in cash

        curve[i] = equity
        peak = max(peak, equity)
        max_dd = max(max_dd, 1.0 - equity / peak)

    years = (dates[-1] - dates[0]).days / 365.25
    cagr = None if equity <= 0 else (equity / cfg.equity0) ** (1 / years) - 1

    return StressResult(
        label=f"{cfg.n_mes:g}MES/{cfg.n_zt:g}ZT/{cfg.n_zn:g}ZN [{cfg.mode}]",
        final_equity=equity, peak_equity=float(np.max(curve)),
        min_equity=float(np.min(curve)), max_drawdown=max_dd, cagr=cagr,
        ruined=ruined, margin_breach=breach,
        curve=pd.Series(curve, index=dates), attrib=attrib,
    )


# ---------------------------------------------------------------------------
def describe_portfolio(cfg: StressConfig) -> str:
    cur = current_levels(cfg)
    lines = []
    lines.append(f"Starting levels (as of {cur['asof_equity'].date()} equity / "
                 f"{cur['asof_rates'].date()} rates):")
    lines.append(f"  S&P 500 {cur['S']:,.0f}   2y {cur['y2']:.2%}   "
                 f"6.5y(ZN CTD) {cur['y6_5']:.2%}   10y {cur['y10']:.2%}   "
                 f"T-bill {cur['bill']:.2%}")
    mes_notional = cfg.n_mes * 5.0 * cur["S"]
    d_zt = dv01(cur["y2"], cur["y2"], 2.0, 200_000.0)
    d_zn = dv01(cur["y6_5"], cur["y6_5"], 6.5, 100_000.0)
    lines.append(f"  MES notional  {mes_notional:>12,.0f}  "
                 f"({mes_notional/cfg.equity0:.2f}x the {cfg.equity0:,.0f} account)")
    lines.append(f"  ZT  DV01/contract ${d_zt:6.2f}  x {cfg.n_zt:g} = ${cfg.n_zt*d_zt:+8.2f}/bp")
    lines.append(f"  ZN  DV01/contract ${d_zn:6.2f}  x {cfg.n_zn:g} = ${cfg.n_zn*d_zn:+8.2f}/bp")
    lines.append(f"  net DV01 ${cfg.n_zt*d_zt + cfg.n_zn*d_zn:+.2f}/bp  "
                 f"-> a 2s/10s STEEPENER (gains when 2y falls relative to 10y)")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Volcker-era stress test of a futures portfolio.")
    ap.add_argument("--equity", type=float, default=80_000.0)
    ap.add_argument("--start", default="1979-08-06")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--div-yield", type=float, default=0.045)
    ap.add_argument("--margin-mult", type=float, default=1.0)
    args = ap.parse_args()

    base = StressConfig(equity0=args.equity, start=args.start, years=args.years,
                        div_yield=args.div_yield, margin_mult=args.margin_mult)
    print(describe_portfolio(base))
    print()
    rows = []
    for mode in ("delta", "level"):
        for n_mes in (1.0, 2.0):
            cfg = StressConfig(**{**base.__dict__, "mode": mode, "n_mes": n_mes})
            r = run_stress(cfg)
            rows.append(dict(
                mode=mode, MES=n_mes, final=r.final_equity,
                cagr=(np.nan if r.cagr is None else r.cagr),
                maxdd=r.max_drawdown, minEq=r.min_equity,
                breach=("-" if r.margin_breach is None else str(r.margin_breach.date())),
                cash=r.attrib["cash"], mes_pnl=r.attrib["MES"],
                zt=r.attrib["ZT"], zn=r.attrib["ZN"],
            ))
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))


if __name__ == "__main__":
    main()
