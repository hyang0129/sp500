"""Run the futures portfolio through every US recession since 1976.

NBER business-cycle peaks/troughs. For each recession we evaluate three windows,
because for a 2s/10s steepener the recession itself is usually *not* where the
damage happens:

    pre      12 months before the peak   -- the tightening/inversion run-up
    during   peak -> trough              -- the recession proper (Fed cutting)
    cycle    pre-start -> trough + 12m   -- the whole round trip

Curve context is reported alongside, since the position is a direct bet on the
2s/10s slope.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from stress_test import StressConfig, current_levels, load_panel, run_stress


@dataclass(frozen=True)
class Recession:
    name: str
    peak: str    # NBER peak (recession starts)
    trough: str  # NBER trough (recession ends)
    note: str = ""


# NBER-dated US recessions covered by the data (equity series starts 1976-06).
RECESSIONS: List[Recession] = [
    Recession("1980 Volcker I", "1980-01-02", "1980-07-31",
              "Volcker shock; credit controls; sharpest rate round-trip on record"),
    Recession("1981-82 Volcker II", "1981-07-01", "1982-11-30",
              "double-dip; Fed holds rates high to break inflation"),
    Recession("1990-91 Gulf/S&L", "1990-07-02", "1991-03-29", "oil spike, S&L crisis"),
    Recession("2001 dot-com", "2001-03-01", "2001-11-30", "tech bust, 9/11"),
    Recession("2007-09 GFC", "2007-12-03", "2009-06-30", "global financial crisis"),
    Recession("2020 COVID", "2020-02-03", "2020-04-30", "pandemic crash, 2 months"),
]


def curve_context(cfg: StressConfig, start: str, end: str) -> dict:
    """2s/10s behaviour over a window, in the replayed (delta) space."""
    sub = StressConfig(**{**cfg.__dict__, "start": start, "end": end})
    win = load_panel(sub)
    cur = current_levels(sub)
    d0 = win.iloc[0]
    if cfg.mode == "delta":
        y2 = cur["y2"] * 100 + (win["y2"] - d0["y2"]) * 100
        y10 = cur["y10"] * 100 + (win["y10"] - d0["y10"]) * 100
        y2, y10 = y2.clip(lower=5e-2), y10.clip(lower=5e-2)
    else:
        y2, y10 = win["y2"] * 100, win["y10"] * 100
    sp = y10 - y2
    return dict(
        y2_start=y2.iloc[0], y2_end=y2.iloc[-1], d_y2=(y2.iloc[-1] - y2.iloc[0]) * 100,
        spread_start=sp.iloc[0], spread_end=sp.iloc[-1],
        d_spread=(sp.iloc[-1] - sp.iloc[0]) * 100,  # bp, + = steepened
        spread_min=sp.min() * 100, spread_max=sp.max() * 100,  # bp
    )


def windows_for(r: Recession, pre_months: int = 12, post_months: int = 12):
    peak, trough = pd.Timestamp(r.peak), pd.Timestamp(r.trough)
    return {
        "pre": (str((peak - pd.DateOffset(months=pre_months)).date()), r.peak),
        "during": (r.peak, r.trough),
        "cycle": (str((peak - pd.DateOffset(months=pre_months)).date()),
                  str((trough + pd.DateOffset(months=post_months)).date())),
    }


def run_recessions(cfg: StressConfig, pre_months: int = 12, post_months: int = 12) -> pd.DataFrame:
    rows = []
    for r in RECESSIONS:
        for wname, (a, b) in windows_for(r, pre_months, post_months).items():
            sub = StressConfig(**{**cfg.__dict__, "start": a, "end": b})
            try:
                res = run_stress(sub)
                cc = curve_context(cfg, a, b)
            except ValueError:
                continue
            rows.append(dict(
                recession=r.name, window=wname, start=a[:7], end=b[:7],
                ret=res.final_equity / cfg.equity0 - 1.0,
                pnl=res.final_equity - cfg.equity0,
                maxDD=res.max_drawdown, minEq=res.min_equity,
                breach=("-" if res.margin_breach is None else str(res.margin_breach.date())),
                d_spread_bp=cc["d_spread"], spread_min_bp=cc["spread_min"],
                d_y2_bp=cc["d_y2"],
                cash=res.attrib["cash"], MES=res.attrib["MES"],
                ZT=res.attrib["ZT"], ZN=res.attrib["ZN"],
            ))
    return pd.DataFrame(rows)


def describe(cfg: StressConfig) -> str:
    from futures import dv01
    cur = current_levels(cfg)
    d_zt = dv01(cur["y2"], cur["y2"], 2.0, 200_000.0)
    d_zn = dv01(cur["y6_5"], cur["y6_5"], 6.5, 100_000.0)
    mes_n = cfg.n_mes * 5.0 * cur["S"]
    marg = (abs(cfg.n_mes) * 2400 + abs(cfg.n_zt) * 1300 + abs(cfg.n_zn) * 2200)
    net = cfg.n_zt * d_zt + cfg.n_zn * d_zn
    return (
        f"Account ${cfg.equity0:,.0f}   {cfg.n_mes:g} MES / {cfg.n_zt:g} ZT / {cfg.n_zn:g} ZN\n"
        f"  MES notional ${mes_n:,.0f} ({mes_n/cfg.equity0:.2f}x)   "
        f"ZT {cfg.n_zt*d_zt:+.0f}/bp   ZN {cfg.n_zn*d_zn:+.0f}/bp   net {net:+.0f}/bp\n"
        f"  margin ${marg:,.0f} = {marg/cfg.equity0:.1%} of account"
    )


# ---------------------------------------------------------------------------
def chart_recessions(cfg: StressConfig, path: str = "output/recession_scorecard.png"):
    """Pre-recession vs in-recession returns, plus the continuous Volcker path."""
    import os
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = run_recessions(cfg)
    names = [r.name for r in RECESSIONS]
    pre = [df[(df.recession == n) & (df.window == "pre")]["ret"].iloc[0] * 100 for n in names]
    dur = [df[(df.recession == n) & (df.window == "during")]["ret"].iloc[0] * 100 for n in names]
    ddp = [df[(df.recession == n) & (df.window == "pre")]["maxDD"].iloc[0] * 100 for n in names]
    ddd = [df[(df.recession == n) & (df.window == "during")]["maxDD"].iloc[0] * 100 for n in names]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12))
    x = np.arange(len(names))
    ax1.bar(x - 0.2, pre, 0.4, color="firebrick", label="12m BEFORE (tightening/inversion)")
    ax1.bar(x + 0.2, dur, 0.4, color="seagreen", label="DURING recession (Fed cutting)")
    ax1.axhline(0, color="black", lw=0.8)
    ax1.set_xticks(x); ax1.set_xticklabels(names, fontsize=8, rotation=12)
    ax1.set_ylabel("return (%)")
    ax1.set_title("2s/10s steepener + equity: the pain is BEFORE the recession, not during it")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3, axis="y")

    ax2.bar(x - 0.2, ddp, 0.4, color="firebrick", label="12m before")
    ax2.bar(x + 0.2, ddd, 0.4, color="seagreen", label="during")
    ax2.set_xticks(x); ax2.set_xticklabels(names, fontsize=8, rotation=12)
    ax2.set_ylabel("max drawdown (%)")
    ax2.set_title("Max drawdown by window")
    ax2.legend(fontsize=8); ax2.grid(alpha=0.3, axis="y")

    vc = StressConfig(**{**cfg.__dict__, "start": "1979-01-02", "end": "1984-01-03"})
    rv = run_stress(vc)
    ax3.plot(rv.curve.index, rv.curve.values, color="steelblue", lw=1.6)
    ax3.axhline(cfg.equity0, color="black", lw=0.8, ls="--", label=f"start ${cfg.equity0:,.0f}")
    ax3.axhline(2 * 2400 + 4 * 1300 + 2 * 2200, color="firebrick", lw=1.0, ls=":",
                label="margin requirement")
    ax3.annotate(f"trough ${rv.curve.min():,.0f}\n({rv.max_drawdown:.0%} DD)",
                 xy=(rv.curve.idxmin(), rv.curve.min()),
                 xytext=(0.28, 0.15), textcoords="axes fraction", fontsize=9,
                 arrowprops=dict(arrowstyle="->", color="firebrick"))
    ax3.set_ylabel("equity ($)")
    ax3.set_title("Continuous Volcker path 1979-01 -> 1984-01 (both dips, compounding)")
    ax3.legend(fontsize=8); ax3.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print(f"Wrote {path}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Run the futures book through US recessions.")
    ap.add_argument("--equity", type=float, default=100_000.0)
    ap.add_argument("--mes", type=float, default=2.0)
    ap.add_argument("--zt", type=float, default=4.0)
    ap.add_argument("--zn", type=float, default=-2.0)
    ap.add_argument("--mode", default="delta", choices=["delta", "level"])
    ap.add_argument("--chart", action="store_true", help="also write the scorecard chart")
    a = ap.parse_args()

    cfg = StressConfig(equity0=a.equity, n_mes=a.mes, n_zt=a.zt, n_zn=a.zn, mode=a.mode)
    print(describe(cfg))
    print()
    df = run_recessions(cfg)
    show = df[["recession", "window", "start", "end", "ret", "maxDD", "minEq",
               "breach", "d_spread_bp", "spread_min_bp", "MES", "ZT", "ZN"]]
    print(show.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    print("\n=== continuous Volcker path 1979-01 -> 1984-01 (both dips, compounding) ===")
    rv = run_stress(StressConfig(**{**cfg.__dict__, "start": "1979-01-02", "end": "1984-01-03"}))
    print(f"  final ${rv.final_equity:,.0f} ({rv.final_equity/cfg.equity0:.2f}x)  "
          f"CAGR {rv.cagr:.2%}  maxDD {rv.max_drawdown:.1%}  "
          f"trough ${rv.min_equity:,.0f} on {rv.curve.idxmin().date()}  "
          f"margin call: {rv.margin_breach or 'NONE'}")

    if a.chart:
        chart_recessions(cfg)
