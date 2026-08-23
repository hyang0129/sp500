"""Intra-period wipeout and margin-call thresholds for a monthly-reset book.

A monthly-reset leveraged book holds a FIXED notional within the month, so
during the month its equity moves linearly with the index:

    equity_t / equity_0  =  1 + L * cum_return_since_month_start

Two thresholds follow, and they are not the same:

    wipeout      equity hits zero          ->  L >= 1 / |worst intra-month drop|
    margin call  equity < mm * notional    ->  L >= 1 / (mm + |worst drop|)

The margin call binds FIRST and is the one that actually ends the account: a
broker liquidates at the maintenance level, it does not wait for zero. Exchanges
also raise margin requirements in a crisis (CME did so sharply in October 1987),
which pulls the threshold lower still.

This matters because a leverage sweep run on the post-1988 total-return series
never sees October 1987 - the single most dangerous day for a leveraged book -
and a model that only liquidates at exactly zero equity overstates survivable
leverage by roughly 0.6x.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from config import Config
from data import prepare

# MES maintenance margin ~ $2,400 on ~$38k notional.
MES_MAINTENANCE = 0.065


def intramonth_drops(cfg: Config | None = None) -> pd.Series:
    """Worst cumulative drop from month start, per calendar month."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        d = prepare(cfg or Config())
    grp = pd.Series(d.index.year * 12 + d.index.month, index=d.index)
    cum = (1 + d["tr"]).groupby(grp).cumprod() - 1.0
    worst = cum.groupby(grp).min()
    worst.index = [d.index[grp == k][0].strftime("%Y-%m") for k in worst.index]
    return worst


def wipeout_leverage(drop: float) -> float:
    """Leverage at which a monthly-reset book hits zero equity."""
    return 1.0 / abs(drop)


def margin_call_leverage(drop: float, maintenance: float = MES_MAINTENANCE) -> float:
    """Leverage at which a monthly-reset book breaches maintenance margin."""
    return 1.0 / (maintenance + abs(drop))


def table(n: int = 8, maintenance: float = MES_MAINTENANCE) -> pd.DataFrame:
    w = intramonth_drops().nsmallest(n)
    return pd.DataFrame({
        "month": w.index,
        "intra_month_drop": w.values,
        "margin_called_at": [margin_call_leverage(v, maintenance) for v in w.values],
        "wiped_at": [wipeout_leverage(v) for v in w.values],
    })


def main():
    df = table()
    print(f"Monthly-reset book, maintenance margin = {MES_MAINTENANCE:.1%} of notional\n")
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    worst = df.iloc[0]
    print(f"\nBinding constraint from {worst['month']} ({worst['intra_month_drop']:.2%}):")
    print(f"  margin call at L >= {worst['margin_called_at']:.2f}x")
    print(f"  wipeout     at L >= {worst['wiped_at']:.2f}x")
    print("\nSurvivability of the October 1987 month at common leverages:")
    d87 = float(worst["intra_month_drop"])
    for L in (1.0, 1.5, 2.0, 2.5, 2.73, 3.0, 3.33):
        eq = 1 + L * d87
        called = L >= margin_call_leverage(d87)
        state = "WIPED" if eq <= 0 else ("MARGIN CALL" if called else "survives")
        print(f"  {L:>5.2f}x -> equity {eq:>7.1%} of month-start   {state}")




def reset_scheme_ceilings(maintenance: float = MES_MAINTENANCE) -> pd.DataFrame:
    """Survivable leverage under each reset scheme.

    Monthly reset carries a stale notional all month, so the whole month's
    drawdown lands on one fixed exposure. Daily reset re-strikes the notional
    every day, so only a single day's move can breach margin. That makes daily
    reset survive MORE leverage than monthly, despite its volatility decay —
    the opposite of the usual "monthly is gentler" intuition.
    """
    w = intramonth_drops()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tr = prepare(Config())["tr"]
    return pd.DataFrame([
        dict(reset="monthly", worst_move=w.min(), what="worst month",
             margin_call_at=margin_call_leverage(w.min(), maintenance)),
        dict(reset="daily", worst_move=tr.min(), what="worst day",
             margin_call_at=margin_call_leverage(tr.min(), maintenance)),
    ])


if __name__ == "__main__":
    main()
