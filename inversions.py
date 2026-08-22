"""Pure curve-flattening screen: the real tail risk of a 2s/10s steepener.

The recession scorecard (recessions.py) conditions on recessions. But this book
is hurt by *flattening*, which does not require a recession to follow — 1994 and
2022-23 both inverted hard without a Volcker-style outcome. This module screens
all of 1976-2026 for the worst flattening episodes regardless of what came next,
and compares three books over each:

    full    2 MES + 4 ZT - 2 ZN   (equity + steepener)
    equity  2 MES only            (does the overlay earn its keep?)
    rates   4 ZT - 2 ZN only      (the overlay standalone)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd

from stress_test import StressConfig, current_levels, load_panel, run_stress

BOOKS = {
    "full":   dict(n_mes=2.0, n_zt=4.0, n_zn=-2.0),
    "equity": dict(n_mes=2.0, n_zt=0.0, n_zn=0.0),
    "rates":  dict(n_mes=0.0, n_zt=4.0, n_zn=-2.0),
}


def spread_series(rates_path="data/treasury_yields_daily.csv",
                  equity_path="data/sp500_daily.csv") -> pd.Series:
    """Historical 2s10s in bp, restricted to dates where equity data also exists."""
    rt = pd.read_csv(rates_path, parse_dates=["date"]).set_index("date")
    eq = pd.read_csv(equity_path, parse_dates=["date"]).set_index("date")
    df = rt.join(eq[["close"]], how="inner").dropna(subset=["y2", "y10"])
    return (df.y10 - df.y2) * 100.0


def find_flattening_episodes(sp: pd.Series, lookback_days: int = 252,
                             n: int = 8, min_gap_days: int = 400
                             ) -> List[Tuple[pd.Timestamp, pd.Timestamp, float]]:
    """Worst non-overlapping `lookback_days` flattening episodes.

    Returns (start, end, change_bp) with change_bp negative = flattened.
    """
    chg = (sp - sp.shift(lookback_days)).dropna().sort_values()
    picked: List[Tuple[pd.Timestamp, pd.Timestamp, float]] = []
    for end, delta in chg.items():
        if all(abs((end - e).days) > min_gap_days for _, e, _ in picked):
            i = sp.index.get_loc(end)
            picked.append((sp.index[max(i - lookback_days, 0)], end, float(delta)))
        if len(picked) >= n:
            break
    return sorted(picked, key=lambda t: t[1])


def compare_books(cfg: StressConfig, start: str, end: str) -> dict:
    """Run all three books over one window."""
    out = {}
    for name, pos in BOOKS.items():
        sub = StressConfig(**{**cfg.__dict__, **pos, "start": start, "end": end})
        r = run_stress(sub)
        out[name] = dict(ret=r.final_equity / cfg.equity0 - 1.0,
                         maxDD=r.max_drawdown, minEq=r.min_equity,
                         breach=r.margin_breach)
    return out


def screen(cfg: StressConfig, n: int = 8, lookback_days: int = 252,
           recovery_months: int = 12) -> pd.DataFrame:
    sp = spread_series(cfg.rates_path, cfg.equity_path)
    eps = find_flattening_episodes(sp, lookback_days=lookback_days, n=n)
    rows = []
    for a, b, delta in eps:
        rec_end = min(b + pd.DateOffset(months=recovery_months), sp.index[-1])
        for phase, (s, e) in {"flattening": (a, b), "+12m after": (b, rec_end)}.items():
            if (e - s).days < 40:
                continue
            try:
                cmp = compare_books(cfg, str(s.date()), str(e.date()))
            except ValueError:
                continue
            rows.append(dict(
                episode=f"{a.date()}..{b.date()}", phase=phase,
                d_spread_bp=delta if phase == "flattening" else np.nan,
                spread_end_bp=sp[b],
                full=cmp["full"]["ret"], equity=cmp["equity"]["ret"], rates=cmp["rates"]["ret"],
                full_DD=cmp["full"]["maxDD"], equity_DD=cmp["equity"]["maxDD"],
                edge=cmp["full"]["ret"] - cmp["equity"]["ret"],
            ))
    return pd.DataFrame(rows)


def rolling_compare(cfg: StressConfig, window_years: int = 5, step_months: int = 3
                    ) -> pd.DataFrame:
    """Distribution of full-vs-equity outcomes over all rolling windows 1976-2026."""
    panel = load_panel(StressConfig(**{**cfg.__dict__, "start": "1976-06-02",
                                       "end": "2026-08-14"}))
    dates = panel.index
    rows = []
    cur = dates[0]
    last = dates[-1] - pd.DateOffset(years=window_years)
    while cur <= last:
        end = cur + pd.DateOffset(years=window_years)
        try:
            cmp = compare_books(cfg, str(cur.date()), str(min(end, dates[-1]).date()))
        except ValueError:
            cur += pd.DateOffset(months=step_months)
            continue
        rows.append(dict(start=cur.date(),
                         full=cmp["full"]["ret"], equity=cmp["equity"]["ret"],
                         rates=cmp["rates"]["ret"],
                         full_DD=cmp["full"]["maxDD"], equity_DD=cmp["equity"]["maxDD"],
                         edge=cmp["full"]["ret"] - cmp["equity"]["ret"]))
        cur += pd.DateOffset(months=step_months)
    return pd.DataFrame(rows)


def summarize_rolling(df: pd.DataFrame) -> str:
    def q(s, p):
        return np.percentile(s, p)
    lines = [f"n windows = {len(df)}"]
    lines.append(f"{'':10s} {'median':>9} {'5th pct':>9} {'25th':>9} {'75th':>9} {'worst':>9} {'medDD':>8} {'worstDD':>8}")
    for name in ("full", "equity", "rates"):
        s = df[name] * 100
        dd = df.get(f"{name}_DD")
        ddm = f"{np.median(dd)*100:7.1f}%" if dd is not None else "     n/a"
        ddw = f"{dd.max()*100:7.1f}%" if dd is not None else "     n/a"
        lines.append(f"{name:10s} {np.median(s):8.1f}% {q(s,5):8.1f}% {q(s,25):8.1f}% "
                     f"{q(s,75):8.1f}% {s.min():8.1f}% {ddm:>8} {ddw:>8}")
    e = df["edge"] * 100
    lines.append("")
    lines.append(f"overlay edge (full - equity): median {np.median(e):+.1f}pp, "
                 f"5th {q(e,5):+.1f}pp, 95th {q(e,95):+.1f}pp, "
                 f"wins {100*(e>0).mean():.0f}% of windows")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
def chart_comparison(cfg: StressConfig, path: str = "output/inversion_comparison.png"):
    """Flattening episodes and the risk/return of the overlay vs plain MES."""
    import os
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = screen(cfg)
    fl = df[df.phase == "flattening"].reset_index(drop=True)
    labels = [e.split("..")[1][:7] for e in fl.episode]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 13))
    x = np.arange(len(fl))
    ax1.bar(x - 0.2, fl["equity"] * 100, 0.4, color="steelblue", label="2 MES only")
    ax1.bar(x + 0.2, fl["full"] * 100, 0.4, color="firebrick", label="2 MES + steepener")
    ax1.axhline(0, color="black", lw=0.8)
    ax1.set_xticks(x); ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_ylabel("return over the flattening (%)")
    ax1.set_title("Worst curve-flattening episodes since 1976 — the overlay loses EVERY time")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3, axis="y")
    for i, v in enumerate(fl["edge"] * 100):
        ax1.annotate(f"{v:+.0f}pp", (i, min(fl['full'][i], fl['equity'][i]) * 100 - 3),
                     ha="center", fontsize=7, color="firebrick")

    # equity-crisis windows: where the overlay earns its keep
    from recessions import RECESSIONS, windows_for
    names, fulls, eqs = [], [], []
    for rec in RECESSIONS:
        a, b = windows_for(rec)["during"]
        c = compare_books(cfg, a, b)
        names.append(rec.name.split()[0]); fulls.append(c["full"]["ret"] * 100)
        eqs.append(c["equity"]["ret"] * 100)
    x2 = np.arange(len(names))
    ax2.bar(x2 - 0.2, eqs, 0.4, color="steelblue", label="2 MES only")
    ax2.bar(x2 + 0.2, fulls, 0.4, color="seagreen", label="2 MES + steepener")
    ax2.axhline(0, color="black", lw=0.8)
    ax2.set_xticks(x2); ax2.set_xticklabels(names, fontsize=8)
    ax2.set_ylabel("return during recession (%)")
    ax2.set_title("...but during recessions the overlay is a genuine equity hedge")
    ax2.legend(fontsize=8); ax2.grid(alpha=0.3, axis="y")

    # risk/return cloud over rolling windows
    rc = rolling_compare(cfg, window_years=5)
    ax3.scatter(rc.equity_DD * 100, rc.equity * 100, s=12, alpha=0.5,
                color="steelblue", label="2 MES only")
    ax3.scatter(rc.full_DD * 100, rc.full * 100, s=12, alpha=0.5,
                color="firebrick", label="2 MES + steepener")
    ax3.set_xlabel("max drawdown over the 5y window (%)")
    ax3.set_ylabel("5y return (%)")
    ax3.set_title("Rolling 5-year windows, 1976-2026: the overlay pushes RIGHT (more risk) "
                  "more than UP (more return)")
    ax3.legend(fontsize=8); ax3.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print(f"Wrote {path}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Curve-flattening screen + overlay comparison.")
    ap.add_argument("--equity", type=float, default=100_000.0)
    ap.add_argument("--mode", default="delta", choices=["delta", "level"])
    ap.add_argument("--window-years", type=int, default=5)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--chart", action="store_true")
    a = ap.parse_args()

    cfg = StressConfig(equity0=a.equity, mode=a.mode, **BOOKS["full"])

    print("=== WORST FLATTENING EPISODES SINCE 1976 (regardless of recession) ===")
    print("    full = 2 MES + 4 ZT - 2 ZN   equity = 2 MES only   rates = overlay only\n")
    df = screen(cfg, n=a.n)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    print(f"\n=== ROLLING {a.window_years}-YEAR WINDOWS, 1976-2026 (delta replay) ===")
    rc = rolling_compare(cfg, window_years=a.window_years)
    print(summarize_rolling(rc))

    if a.chart:
        chart_comparison(cfg)
