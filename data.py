"""Load and validate the daily data, and derive the series the model needs.

The committed CSV (data/sp500_daily.csv) is sourced by fetch_data.py from
Yahoo Finance and has columns:
    date, total_return_index, close, vix, rf_annual

This module turns that into a clean daily frame with:
    tr      : daily *total* return of the index (the levered-engine driver)
    S       : price-index level (the underlying for option strikes/payoffs)
    rf_annual, rf_daily : financing rate (decimal, annual and per-day)
    sigma   : pricing vol (decimal) = VIX/100 where available, else trailing
              realized vol; used only at roll dates for Black-Scholes.
    div_yield : time-varying annual dividend yield (decimal). Used as the BS
              dividend term q, and as the pre-1988 total-return add-back.
    real_tr : bool, True where `tr` came from the genuine total-return index
              (False where it was approximated from price + a dividend yield).
    has_rf  : bool, True where a genuine financing rate is available (1934+);
              leverage > 1 is only meaningful here.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from config import Config


def load_raw(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
    df = df.set_index("date")
    expected = {"close"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing required column(s): {missing}")
    # Forward-fill sparse financing / vol; leave leading NaNs intact.
    if "rf_annual" in df:
        df["rf_annual"] = df["rf_annual"].ffill()
    if "vix" in df:
        df["vix"] = df["vix"].ffill()
    return df


def prepare(cfg: Config) -> pd.DataFrame:
    """Build the analysis frame used by the backtest engine."""
    raw = load_raw(cfg.data_path)
    n = len(raw)
    out = pd.DataFrame(index=raw.index)
    out["S"] = raw["close"].astype(float)

    # --- dividend yield (time-varying where sourced, else flat default) -----
    if "div_yield" in raw and raw["div_yield"].notna().any():
        div_yield = raw["div_yield"].astype(float).ffill().bfill()
    else:
        div_yield = pd.Series(cfg.div_yield, index=raw.index)
    out["div_yield"] = div_yield

    # --- daily total return ------------------------------------------------
    price_ret = raw["close"].pct_change()
    div_daily = div_yield / cfg.trading_days_per_year
    approx_tr = price_ret + div_daily
    real_tr_mask = pd.Series(False, index=raw.index)

    if cfg.use_total_return and "total_return_index" in raw and raw["total_return_index"].notna().any():
        tri = raw["total_return_index"]
        tr_from_index = tri.pct_change()
        have = tri.notna() & tri.shift().notna()
        tr = tr_from_index.where(have, approx_tr)
        real_tr_mask = have
        if (~have).sum() > 1:  # first row is always NaN pct_change
            warnings.warn(
                f"Total-return index covers {int(have.sum())}/{n} rows; "
                f"{int((~have).sum())} rows use a time-varying dividend-yield "
                "add-back approximation (Shiller D/P pre-1988).",
                stacklevel=2,
            )
    else:
        tr = approx_tr
        warnings.warn(
            "No total-return index available: approximating dividends with the "
            "time-varying dividend yield. Over 20y of leveraged compounding "
            "this materially affects results.",
            stacklevel=2,
        )
    out["tr"] = tr
    out["real_tr"] = real_tr_mask

    # --- financing ---------------------------------------------------------
    if "rf_annual" not in raw or raw["rf_annual"].isna().all():
        warnings.warn("No financing rate found; using 0%. (L>1) results unrealistic.", stacklevel=2)
        out["rf_annual"] = 0.0
        out["has_rf"] = False
    else:
        out["has_rf"] = raw["rf_annual"].notna().to_numpy()
        out["rf_annual"] = raw["rf_annual"].astype(float).ffill().fillna(0.0)
    out["rf_daily"] = out["rf_annual"] / cfg.trading_days_per_year

    # --- pricing vol -------------------------------------------------------
    realized = (
        out["tr"].rolling(cfg.realized_vol_window).std() * np.sqrt(cfg.trading_days_per_year)
    )
    if cfg.vol_source == "vix" and "vix" in raw and raw["vix"].notna().any():
        sigma = raw["vix"].astype(float) / 100.0
        sigma = sigma.where(sigma.notna(), realized)
    else:
        sigma = realized
    # Fill any residual gaps (e.g. start of series) with a sane constant.
    out["sigma"] = sigma.ffill().bfill().fillna(0.18)

    # Drop the first row (NaN return).
    out = out.iloc[1:].copy()
    return out
