"""Extract daily 2y and 10y Treasury par yields from the Fed's GSW curve file.

Source: Gurkaynak-Sack-Wright (GSW) fitted nominal yield curve, published by the
Federal Reserve Board as feds200628.csv. We take the *par* yields
(coupon-equivalent, mnemonics SVENPY02 / SVENPY10) because Treasury note futures
track coupon-bearing notes, not zeros.

Coverage is daily from 1961 (2y) / 1971 (10y), which spans the Volcker era.

We also keep the 5y/6y/7y points because the cheapest-to-deliver note behind the
10-year future (ZN) is a ~6.5-year note, not a 10-year one; pricing ZN off the
6.5y point is materially more accurate than off the 10y point.

Output: data/treasury_yields_daily.csv with columns
  date, y2, y5, y6, y7, y10   (par yields, percent).
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
GSW_URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
OUT = "data/treasury_yields_daily.csv"


def fetch_gsw(retries: int = 4) -> pd.DataFrame:
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(GSW_URL, headers={"User-Agent": UA}, timeout=120)
            r.raise_for_status()
            text = r.text
            # The file carries a preamble; the real table starts at the "Date," header.
            idx = text.index("\nDate,")
            return pd.read_csv(io.StringIO(text[idx + 1 :]))
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 2 ** (attempt + 1)
            print(f"  GSW fetch failed ({e}); retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch GSW curve: {last}")


def main() -> None:
    print("Fetching Fed GSW yield-curve file (~16MB) ...")
    raw = fetch_gsw()
    cols = {"SVENPY02": "y2", "SVENPY05": "y5", "SVENPY06": "y6",
            "SVENPY07": "y7", "SVENPY10": "y10"}
    df = raw[["Date"] + list(cols)].copy()
    df.columns = ["date"] + list(cols.values())
    df["date"] = pd.to_datetime(df["date"])
    for c in cols.values():
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["y2", "y10"]).sort_values("date").set_index("date")
    df.to_csv(OUT, float_format="%.4f")
    print(f"Wrote {OUT}: {len(df)} rows, {df.index.min().date()} -> {df.index.max().date()}")
    volcker = df.loc["1979-08-01":"1989-08-31"]
    print(f"Volcker-era coverage: {len(volcker)} rows")
    print("  2y  range: %.2f%% - %.2f%%" % (volcker.y2.min(), volcker.y2.max()))
    print("  10y range: %.2f%% - %.2f%%" % (volcker.y10.min(), volcker.y10.max()))
    print(df.tail(2).to_string())


if __name__ == "__main__":
    main()
