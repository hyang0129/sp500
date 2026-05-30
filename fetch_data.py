"""Source daily S&P 500 data from Yahoo Finance and write a committed CSV.

Sources (Yahoo Finance v8 chart API, requires a browser User-Agent):
  ^SP500TR : S&P 500 *total return* index level (dividends reinvested). Primary.
  ^GSPC    : S&P 500 *price* index level (used for dividend-yield approximation
             fallback and to extend history before ^SP500TR begins in 1988).
  ^VIX     : CBOE volatility index (implied vol proxy for 1y option pricing).
  ^IRX     : 13-week US T-bill yield (annualized %, the financing-cost proxy).

Output: data/sp500_daily.csv with columns
  date, total_return_index, close, vix, rf_annual

`rf_annual` is a decimal (e.g. 0.045 = 4.5%). `vix` is in points (e.g. 20.0).
This script is run once to source the data; the resulting CSV is committed so
the backtest runs offline and reproducibly.
"""
from __future__ import annotations

import io
import sys
import time

import pandas as pd
import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"

SYMBOLS = {
    "total_return_index": "%5ESP500TR",
    "close": "%5EGSPC",
    "vix": "%5EVIX",
    "irx": "%5EIRX",
}


def fetch_series(symbol: str, retries: int = 4) -> pd.Series:
    """Fetch a daily close series from Yahoo as a date-indexed pandas Series."""
    url = f"{BASE}{symbol}?range=50y&interval=1d"
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            result = data["chart"]["result"][0]
            ts = result["timestamp"]
            closes = result["indicators"]["quote"][0]["close"]
            idx = pd.to_datetime(pd.Series(ts), unit="s").dt.normalize()
            s = pd.Series(closes, index=idx, name=symbol).dropna()
            return s
        except Exception as e:  # noqa: BLE001 - retry on any transient failure
            last_err = e
            wait = 2 ** (attempt + 1)
            print(f"  fetch {symbol} failed ({e}); retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch {symbol}: {last_err}")


def main() -> None:
    frames = {}
    for name, sym in SYMBOLS.items():
        print(f"Fetching {name} ({sym}) ...")
        frames[name] = fetch_series(sym)

    df = pd.DataFrame(frames)
    # ^IRX is a 13-week T-bill yield quoted in percent -> decimal annual rate.
    df["rf_annual"] = df.pop("irx") / 100.0
    df = df.sort_index()
    df.index.name = "date"

    # Forward-fill small interior gaps only. Do NOT back-fill leading NaNs:
    # ^VIX has no data before 1990, and back-filling it with the 1990 value
    # would invent volatility history. The model falls back to trailing
    # realized vol wherever VIX is missing. rf (^IRX) has full coverage.
    df["rf_annual"] = df["rf_annual"].ffill()
    df["vix"] = df["vix"].ffill()

    # Keep rows where we have at least a price (close); TR may start later (1988).
    df = df[df["close"].notna()]

    out = "data/sp500_daily.csv"
    df.to_csv(out, float_format="%.6f")
    print(f"\nWrote {out}: {len(df)} rows, {df.index.min().date()} -> {df.index.max().date()}")
    print(df.tail(3).to_string())
    print("\nColumn coverage (non-null counts):")
    print(df.notna().sum().to_string())


if __name__ == "__main__":
    main()
