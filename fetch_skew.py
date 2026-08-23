"""Source the CBOE SKEW index and the CBOE S&P 500 PutWrite index (PUT).

^SKEW  CBOE SKEW index, 1990-> . Defined as SKEW = 100 - 10 * g1, where g1 is
       the *risk-neutral skewness* of the 30-day S&P 500 log return implied by
       the option surface. SKEW = 100 means a lognormal (no skew) market;
       higher SKEW means a fatter, more expensive left tail.

^PUT   CBOE S&P 500 PutWrite Index, 1996-> . A real, published, fully
       collateralised strategy that sells **at-the-money** 1-month SPX puts and
       holds them to expiry. Because it is struck ATM it is almost unaffected by
       skew, which makes it the ideal benchmark for validating the mechanics of
       a put-writing engine (premium capture, settlement, collateral interest)
       independently of any smile assumption.

Output: data/skew_daily.csv with columns  date, skew, put_index
"""
from __future__ import annotations

import sys
import time

import pandas as pd
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
OUT = "data/skew_daily.csv"


def fetch(symbol: str, retries: int = 4) -> pd.Series:
    url = f"{BASE}{symbol}?range=50y&interval=1d"
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            r.raise_for_status()
            res = r.json()["chart"]["result"][0]
            idx = pd.to_datetime(pd.Series(res["timestamp"]), unit="s").dt.normalize()
            return pd.Series(res["indicators"]["quote"][0]["close"], index=idx).dropna()
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 2 ** (attempt + 1)
            print(f"  {symbol} failed ({e}); retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch {symbol}: {last}")


def main() -> None:
    print("Fetching ^SKEW ...")
    skew = fetch("%5ESKEW")
    print("Fetching ^PUT (CBOE PutWrite) ...")
    put = fetch("%5EPUT")
    df = pd.DataFrame({"skew": skew, "put_index": put}).sort_index()
    df.index.name = "date"
    df = df[df.index >= "1990-01-01"]
    df.to_csv(OUT, float_format="%.4f")
    print(f"\nWrote {OUT}: {len(df)} rows, {df.index.min().date()} -> {df.index.max().date()}")
    s = df["skew"].dropna()
    print(f"  SKEW: min {s.min():.1f} ({s.idxmin().date()})  "
          f"max {s.max():.1f} ({s.idxmax().date()})  median {s.median():.1f}")
    print(f"  implied risk-neutral skewness g1 = (100 - SKEW)/10: "
          f"median {(100 - s.median())/10:.2f}, range "
          f"{(100 - s.max())/10:.2f} to {(100 - s.min())/10:.2f}")
    print(f"  PUT index non-null: {df['put_index'].notna().sum()}")


if __name__ == "__main__":
    main()
