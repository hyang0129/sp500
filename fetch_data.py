"""Source daily S&P 500 data from Yahoo Finance (+ FRED + Shiller) and write a
committed CSV that reaches back to the 1930s.

Sources:
  ^SP500TR : S&P 500 *total return* index level (dividends reinvested). The
             genuine total-return driver, but only available from 1988.
  ^GSPC    : S&P 500 *price* index level. Daily back to 1927-12-30 on Yahoo --
             this is what extends the history through the 1929-32 crash, the
             1970s-80s high-rate era, and 1987.
  ^VIX     : CBOE volatility index (implied-vol proxy). Only from 1990; before
             that the model falls back to trailing realized vol.
  ^IRX     : 13-week US T-bill yield (daily, ~1976+). Financing-cost proxy.
  FRED TB3MS: 3-month T-bill secondary-market rate (monthly, 1934+). Splices in
             the pre-1976 financing rate so leveraged results are realistic in
             the high-rate era.
  Shiller  : monthly S&P price (P) and trailing annual dividend (D) back to 1871.
             Gives a *time-varying* dividend yield (D/P) for the pre-1988
             total-return add-back, replacing a flat assumption.

Output: data/sp500_daily.csv with columns
  date, total_return_index, close, vix, rf_annual, div_yield

`rf_annual` and `div_yield` are decimals (0.045 = 4.5%). `vix` is in points.
The resulting CSV is committed so the backtest runs offline and reproducibly.
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
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
SHILLER = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"

# Yahoo symbols (URL-encoded ^). period1 reaches before ^GSPC's 1927 start.
SYMBOLS = {
    "total_return_index": "%5ESP500TR",
    "close": "%5EGSPC",
    "vix": "%5EVIX",
    "irx": "%5EIRX",
}


def _get(url: str, retries: int = 4, timeout: int = 30, ua: str = UA) -> requests.Response:
    last = None
    headers = {"User-Agent": ua} if ua else {}
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:  # noqa: BLE001 - retry on any transient failure
            last = e
            wait = 2 ** (attempt + 1)
            print(f"  GET failed ({e}); retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Failed GET {url}: {last}")


def fetch_yahoo(symbol: str) -> pd.Series:
    """Daily close series from Yahoo. period1<0 asks for the full history."""
    url = f"{YAHOO}{symbol}?period1=-2208988800&period2=1900000000&interval=1d"
    data = _get(url).json()
    result = data["chart"]["result"][0]
    ts = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    idx = pd.to_datetime(pd.Series(ts), unit="s").dt.normalize()
    return pd.Series(closes, index=idx, name=symbol).dropna()


def fetch_fred_tb3ms() -> pd.Series:
    """Monthly 3-month T-bill rate (decimal), 1934+, for the pre-1976 splice."""
    # FRED's fredgraph endpoint rejects a browser User-Agent (503); use the
    # default requests UA instead.
    txt = _get(f"{FRED}TB3MS", ua="").text
    df = pd.read_csv(io.StringIO(txt))
    df.columns = ["date", "rate"]
    s = pd.Series(
        pd.to_numeric(df["rate"], errors="coerce").values / 100.0,
        index=pd.to_datetime(df["date"]).dt.normalize(),
        name="tb3ms",
    ).dropna()
    return s


def fetch_shiller_div_yield() -> pd.Series:
    """Monthly trailing dividend yield (D/P, decimal) from Shiller, 1871+."""
    content = _get(SHILLER).content
    df = pd.read_excel(io.BytesIO(content), sheet_name="Data", header=7)
    df = df[["Date", "P", "D"]].dropna(subset=["Date", "P", "D"])
    # Shiller's Date is YYYY.MM as a float (e.g. 1871.10 == Oct 1871).
    yr = df["Date"].astype(float).apply(lambda x: int(x))
    mo = (df["Date"].astype(float) * 100).round().astype(int) % 100
    mo = mo.replace(0, 1).clip(1, 12)
    idx = pd.to_datetime(dict(year=yr, month=mo, day=1))
    dy = (df["D"].astype(float) / df["P"].astype(float))
    return pd.Series(dy.values, index=idx, name="div_yield").sort_index()


def main() -> None:
    print("Fetching Yahoo series ...")
    frames = {name: fetch_yahoo(sym) for name, sym in SYMBOLS.items()}
    df = pd.DataFrame(frames).sort_index()
    df.index.name = "date"

    # --- financing rate: daily ^IRX where available, else monthly TB3MS -------
    print("Fetching FRED TB3MS (pre-1976 financing) ...")
    tb = fetch_fred_tb3ms()
    irx = (df.pop("irx") / 100.0)  # ^IRX quoted in percent
    # Reindex TB3MS (monthly) onto the daily calendar and forward-fill.
    tb_daily = tb.reindex(df.index.union(tb.index)).ffill().reindex(df.index)
    rf = irx.where(irx.notna(), tb_daily)
    df["rf_annual"] = rf.ffill()

    # --- time-varying dividend yield (for pre-1988 TR add-back) ---------------
    print("Fetching Shiller dividend yield ...")
    dy = fetch_shiller_div_yield()
    dy_daily = dy.reindex(df.index.union(dy.index)).ffill().reindex(df.index)
    # Backfill the leading gap (pre-1871 never happens; pre-first-quote does for
    # a few 1927 days before Shiller's monthly stamp aligns) and default to 1.8%.
    df["div_yield"] = dy_daily.bfill().fillna(0.018)

    df["rf_annual"] = df["rf_annual"].ffill()
    df["vix"] = df["vix"].ffill()

    # Keep rows with at least a price (close). TR starts 1988; rf starts 1934.
    df = df[df["close"].notna()]
    df = df[["total_return_index", "close", "vix", "rf_annual", "div_yield"]]

    out = "data/sp500_daily.csv"
    df.to_csv(out, float_format="%.6f")
    print(f"\nWrote {out}: {len(df)} rows, {df.index.min().date()} -> {df.index.max().date()}")
    print("\nColumn coverage (non-null counts):")
    print(df.notna().sum().to_string())
    print("\nFirst rows with a financing rate (leverage becomes meaningful here):")
    have_rf = df[df["rf_annual"].notna()]
    print(f"  rf starts {have_rf.index.min().date()}")
    print(df.head(2).to_string())
    print(df.tail(2).to_string())


if __name__ == "__main__":
    main()
