# Long-Horizon Leveraged S&P 500 with Tail Protection — Backtest

A configurable historical backtest answering one question:

> For a buy-and-hold investor with a 10–20 year horizon using leveraged S&P 500
> exposure (1x/2x/3x), **does systematically buying cheap out-of-the-money put
> protection raise long-run compound growth (CAGR) and/or survival probability,
> despite being a drag on average (arithmetic) return?**

Long-run wealth is *geometric* (multiplicative). Leverage amplifies volatility
drag and exposes the account to ruin in a single deep drawdown. The hypothesis:
truncating the left tail with annually-rolled OTM puts can *increase* the
geometric growth rate and cut wipeout probability — even after paying the
premium every year — and this may be true at 2x–3x but false at 1x.

**The primary deliverables are CAGR, max drawdown, P(ruin), and 5th-percentile
ending wealth as a function of (leverage × protection strike), over rolling
historical windows.** Arithmetic mean alone is not the point — the
geometric/tail story is.

---

## TL;DR result (1988–2026, monthly rebalance, realistic "marked-up" premiums)

**10-year windows — 20% OTM put vs. unprotected:**

| Leverage | CAGR median | CAGR **mean** | CAGR 5th pct | 5th-pct terminal wealth |
|---|---|---|---|---|
| 1x none → put20 | 10.7% → 9.5% | 10.7% → 9.2% | 0.8% → −0.1% | 1.08× → 0.99× |
| 2x none → put20 | 16.1% → 14.8% | 17.3% → 14.5% | −3.8% → −3.3% | 0.68× → 0.72× |
| 3x none → put20 | 18.8% → **19.2%** | 21.6% → **18.2%** | −11.2% → **−8.0%** | 0.30× → **0.43×** |

At **3x over 10 years**, the put **lowers the arithmetic mean** (21.6%→18.2%)
yet **raises the median CAGR** (18.8%→19.2%) and **raises the 5th-percentile
terminal wealth by ~40%** (0.30×→0.43×). That divergence between mean and
median/tail *is* the volatility-drag result the hypothesis predicts.

At **1x** protection is pure drag — it lowers median, mean, and the tail.
**2x** is the transition: median dips slightly but the survival tail improves.

See [`SUMMARY.md`](SUMMARY.md) for the full plain-language writeup, including the
**20-year caveat** (in this 1988–2026 sample the market recovered within every
20y window, so 20 years of premium drag makes unprotected win the tail at 20y —
the protection edge is concentrated at shorter horizons and higher leverage).

---

## How to run

```bash
pip install -r requirements.txt

# (optional) re-source the daily data from Yahoo Finance into data/sp500_daily.csv
python fetch_data.py

# run the full experiment grid -> output/results.csv  (~3 min, step 1 month)
python experiments.py --step-months 1

# build metric tables (output/summary_*.csv) + charts (output/*.png)
python report.py

# tests
pytest -q
```

Knobs are exposed on `experiments.py` (e.g. `--liquidation month_end`,
`--div-yield 0.0`) and on the `Config` dataclass in `config.py`.

---

## Data

`data/sp500_daily.csv` is committed (sourced once via `fetch_data.py`). Schema:

| column | meaning |
|---|---|
| `date` | trading date |
| `total_return_index` | `^SP500TR` level — dividends reinvested (1988→). **Primary return driver.** |
| `close` | `^GSPC` price-index level (1976→). Underlying for option strikes/payoffs. |
| `vix` | `^VIX` (1990→), implied-vol proxy for 1y put pricing (`sigma = vix/100`). |
| `rf_annual` | `^IRX` 13-week T-bill yield as a decimal — the financing cost of leverage. |

To use your own data, drop in a CSV with at least `date,close` (and optionally
`total_return_index,rf_annual,vix`). Dates are parsed and sorted; `rf`/`vix`
are forward-filled. If `total_return_index` is absent, dividends are
approximated with a flat add-back (default 1.8%/yr) **and a warning is logged**.

The default experiment universe is the genuine-total-return span (1988-01 →
2026-05), evaluated over rolling **5y / 10y / 15y / 20y** windows (monthly
step; e.g. 401 five-year and 221 twenty-year windows).

---

## Model (see the handoff doc for full derivations)

**Leverage (constant-leverage, periodic reset).** Per rebalance period,
`r_levered = L·TR − (L−1)·rf`. Equity is posted as collateral earning `rf`;
futures give exposure `L·E` with excess return `(TR − rf)`. Rebalance frequency:
- `monthly` (primary, "check finances monthly" cadence) — notional fixed within
  a month (linear intra-month), reset at month boundaries.
- `daily` (comparison) — notional reset daily ⇒ multiplicative compounding,
  surfacing leveraged-ETF-style volatility decay (3x: 18.8% median CAGR monthly
  vs **13.5% daily** over 10y — the decay is real and large).

**Liquidation / ruin.** `liquidation_model="daily_path"` (default): step daily
to detect intra-period breaches even when rebalancing monthly; equity ≤
`maintenance_frac` (default 0) ⇒ absorbing zero. `"month_end"` (comparison) only
marks at month end and understates ruin at 3x. *In the 1988–2026 sample, exact
ruin never occurs under monthly rebalancing — a single-month drop large enough
to wipe a monthly-reset 3x account didn't happen — so the tail shows up as deep
drawdowns (95th-pct MDD ≈ 97% at 3x) and low 5th-pctile wealth, not literal 0.*

**Put overlay.** At each annual roll: settle the prior put's payoff
`max(K−S,0)·units`, then buy a new European put with `K=(1−m)·S`, quantity
`units = (L·equity)/S` held fixed for the year, premium paid from equity.
Priced with Black-Scholes (dividend yield `q`), `T=1`, `r=rf`, `sigma` from
VIX (or trailing realized vol when VIX is missing).

**Volatility risk premium.** Index puts trade richer than BS-fair, so we report
two pricing modes: `fair` (sigma as-is) and `marked_up` (sigma×1.2, default for
headline results — the user explicitly cares whether the strategy survives
realistic option costs).

---

## Files

| file | role |
|---|---|
| `config.py` | `Config` dataclass — every knob, with documented defaults |
| `data.py` | load/validate CSV; dividend add-back; rf/vix handling; vol series |
| `model.py` | Black-Scholes pricing + leverage segment engine |
| `backtest.py` | single-path runner (rolls, premiums, liquidation) + rolling-window driver |
| `experiments.py` | the §4 grid → tidy `output/results.csv` |
| `report.py` | §5 metric tables + §7 charts |
| `fetch_data.py` | one-time data sourcing from Yahoo Finance |
| `tests/` | BS value, put-call parity, L=1 reproduces index TR, financing-drag sign |

---

## Caveats (read before trusting any number)

1. **Liquidation model** drives ruin realism. Default `daily_path`. With monthly
   rebalancing, exact ruin is essentially absent in this sample — the danger is
   visible in drawdown/5th-pctile wealth, not P(ruin). Daily rebalancing shows
   much heavier decay.
2. **European, annually-settled puts.** Intra-year, the put does not cushion a
   crash (payoff only credits at the roll) — protection is "partial" mid-crash,
   and its quantity was fixed at the prior roll. A `put_mtm_for_liquidation` flag
   adds an intrinsic-value mark-to-market for the ruin check (default off, to
   match the conservative European model).
3. **Dividends.** Headline results use the genuine total-return index (1988→).
   Pre-1988 or price-only data uses a flat 1.8%/yr add-back (warned).
4. **VRP markup.** Default sigma×1.2. Real index-put richness varies; the `fair`
   mode brackets the optimistic end. Headline tables use `marked_up`.
5. **Sample = 1988–2026.** Covers 2000–02, 2008, 2020, 2022 and the 2023
   high-rate regime, but not the 1970s–80s high-inflation/high-rate era (no TR
   index). 20y-window conclusions are sensitive to the fact that *every* 20y
   window in-sample fully recovered.

---

## Volcker-era futures stress test

A second study in this repo stress-tests a **futures portfolio** (long 1-2 MES +
long 2 ZT + short 1 ZN on $80k) through the daily deltas of the 1979-1989
Volcker inflation cycle. See [`STRESS_VOLCKER.md`](STRESS_VOLCKER.md).

```bash
python fetch_rates.py     # Fed GSW curve -> data/treasury_yields_daily.csv (2y/5y/6y/7y/10y par yields)
python stress_test.py     # headline table
python stress_report.py   # charts -> output/volcker_*.png
```

| file | role |
|---|---|
| `futures.py` | MES/ZT/ZN contract specs, full bond repricing (convexity), DV01 |
| `stress_test.py` | collateralized-futures engine + Volcker delta/level replay |
| `stress_report.py` | equity-curve, attribution and breaking-point charts |
| `fetch_rates.py` | sources 2y/10y Treasury par yields from the Fed GSW curve |

Headline: at the stated size it survives (3.3-4.8x, 24-31% max drawdown, no
margin call); at **3x the size it is margin-called in March 1980**. The risk is
curve *flattening*, not the level of rates.

### Recession scorecard

`recessions.py` runs the futures book through every NBER recession since 1976
(default: $100k, 2 MES / 4 ZT / -2 ZN, a 2s10s steepener). See
[`RECESSIONS.md`](RECESSIONS.md).

```bash
python recessions.py --chart          # table + output/recession_scorecard.png
python recessions.py --mes 2 --zt 4 --zn -2 --equity 100000 --mode level
```

Headline: the book profited in **all six** recessions since 1976 - a recession
is the Fed cutting the front end, which steepens the curve. Its one bad window
is the *pre-recession inversion*: -23% in the 12 months to July 1981, when 2s10s
hit -194bp. The continuous 1979-1984 Volcker path draws down 37.7% to $74,455
but is never margin-called and ends at 2.06x; at 2.5x the size it *is*
margin-called in March 1980.

### Flattening screen — does the steepener overlay earn its keep?

`inversions.py` screens 1976-2026 for the worst curve-flattening episodes
(regardless of recession) and compares the full book against **2 MES alone**.
See [`INVERSIONS.md`](INVERSIONS.md).

```bash
python inversions.py --chart      # episode table + rolling comparison + charts
```

Headline: the overlay loses in **8 of 8** flattening episodes (avg -24pp), and
its worst case is **2022 (-32.5%)**, not Volcker - because stocks and the curve
sold off together. It *is* a real equity hedge in recessions (+21pp average,
turning the GFC from -24.0% into +3.5%), but risk-adjusted it is dominated:
over 180 rolling 5y windows the full book returns +83.7% median at a 21.4%
median drawdown, while plain **3x MES** returns **+105.7%** at a comparable
23.5% drawdown.

### Position sizing: fixed vs constant-leverage

Every stress module accepts a `sizing` mode on `StressConfig`. Fractional
contracts are supported throughout (`fractional=True`, the default; set
`min_contract` to round).

| sizing | meaning |
|---|---|
| `fixed` | hold the stated contract counts (risk falls as equity grows) |
| `constant_leverage` | resize monthly so each leg's notional/equity stays at its inception ratio |
| `constant_dv01` | resize the rates legs so DV01/equity stays constant (accounts for DV01 falling as yields rise) |

```bash
python recessions.py --chart          # add sizing via StressConfig(sizing=...)
```

`fixed` flatters results because the book shrinks relative to a growing account.
Under `constant_leverage` the overlay's edge on the continuous Volcker path
collapses from **+$20.3k to -$0.7k** while still carrying ~3x the drawdown of
plain 2 MES.
