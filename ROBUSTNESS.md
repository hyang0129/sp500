# Robustness Follow-up to the Audit

`AUDIT.md` flagged that the headline findings rested on (1) a single 1988–2026
path sliced into overlapping windows, (2) a `maintenance_frac = 0` ruin model,
and (3) a sample with no high-rate / permanent-impairment era. This document
implements three of the recommended fixes and reports how the conclusions move.

What was added:

- **Extended data** (`fetch_data.py`, `data.py`): daily `^GSPC` back to **1928**,
  FRED `TB3MS` financing back to **1934**, and a **time-varying** Shiller
  dividend yield replacing the flat 1.8% add-back. The backtest can now run over
  1934→2026 (`history="rf"`) — covering the 1929–32 aftermath, WWII, the
  1970s–80s high-rate era, and 1987.
- **Stationary block bootstrap** (`bootstrap.py`): Politis–Romano resampling of
  daily (return, financing, vol, dividend) blocks into independent synthetic
  paths. Replaces the pseudo-replicated overlapping windows.
- **Realistic maintenance margin** (`config.maint_margin_frac`): liquidate when
  equity falls below a fraction of the *period notional*, not at literal zero.

## 0. The overlapping-window problem, quantified

Historical rolling windows (monthly step) vs. their independent content:

| Window | Reported n | Independent windows |
|---|---|---|
| 5y | 401 | ~6.7 |
| 10y | 341 | ~2.8 |
| 15y | 281 | ~1.6 |
| 20y | 221 | **~0.9** |

The bootstrap supplies 1000+ genuinely independent draws per cell instead.

## 1. The "put raises median CAGR" headline does **not** survive (artifact)

3x, 10-year, monthly, marked-up premiums:

| metric | original (historical, 1988+) | bootstrap (1988+ pool) | bootstrap (1934+ pool) |
|---|---|---|---|
| median CAGR, no put | 18.8% | 22.0% | 18.9% |
| median CAGR, 20% put | **19.2% (rises)** | 15.9% (falls) | 14.8% (falls) |
| 5th-pct terminal wealth, no put | 0.30× | 0.28× | 0.13× |
| 5th-pct terminal wealth, 20% put | 0.43× | 0.30× | 0.16× |

The original study's signature result — the put *raising* the median CAGR while
cutting the mean — was a property of the **single 2000→2009 path** (the bottom-5%
"tail" was ~17 overlapping windows all ending at the 2009 trough). Under
independent resampling the put **lowers the median at every horizon and
leverage**: it is insurance, priced roughly fairly, so it costs growth. What
*does* survive is a modest **left-tail** improvement (5th-pct terminal wealth
rises), i.e. the genuine insurance benefit — but not a free lunch on the median.

## 2. The "narrow 10-year sweet spot / 20y loses" conclusion is sample-dependent

The original claim ("the market always recovered within 20y, so protection
loses at 20y") flips once the sample contains worse sequences. In the extended
1934+ bootstrap, the unprotected 3x 20-year **5th-percentile terminal wealth is
0.012× (a 99% loss)** — there *are* deeply underwater 20-year paths — and
protection lifts it (0.012× → 0.034× at 20% OTM). The "20 years always heals the
drawdown" result was an artifact of the one US history where it happened to be
true. Horizon is not the clean dominant variable the original framing claimed.

## 3. P(ruin) ≈ 0 was an artifact of `maintenance_frac = 0`

3x, 10-year, 1934+ bootstrap, 1000 draws. `mtm` = whether the protective put's
mark-to-market value counts toward the margin test:

| maint. margin | strategy | P(ruin) | median CAGR | 5th-pct TW |
|---|---|---|---|---|
| 0% (literal zero) | none | 2.2% | 17.9% | 0.135× |
| 0% | put20 (European) | 2.2% | 15.0% | 0.175× |
| 0% | put20 (mark-to-market) | 0.7% | 14.4% | 0.251× |
| 5% of notional | none | 15.0% | 20.2% | 0.000× |
| 5% | put20 (European) | **15.0%** | 16.3% | 0.000× |
| 5% | put20 (mark-to-market) | **3.6%** | 15.1% | 0.107× |
| 10% of notional | none | 30.2% | 21.7% | 0.000× |
| 10% | put20 (European) | **30.2%** | 17.9% | 0.000× |
| 10% | put20 (mark-to-market) | **14.3%** | 16.2% | 0.000× |

Two findings the original model hid entirely:

1. **A continuously-held 3x book is not ruin-free.** With a realistic margin
   requirement (5–10% of notional is typical for index futures), a 3x book over
   10 years is wiped with **15–30% probability** in resampled histories —
   not the ~0% the literal-zero model reported. (At a stricter 25%-of-notional
   requirement it is *near-certain* ruin.)
2. **An annually-settled European put does not prevent that ruin** (P(ruin)
   identical to unprotected, to three decimals) because its payoff only lands at
   the roll and cannot post value against an intra-month margin call —
   confirming the audit's concern #2. Only a put whose **mark-to-market value
   counts toward margin** roughly halves ruin. So the form of the protection,
   not just its presence, is what determines whether it saves you.

## How to reproduce

```bash
python fetch_data.py                       # rebuild extended 1928-2026 CSV
python bootstrap.py --n-boot 1000 --history rf                 # extended pool
python bootstrap.py --n-boot 1000 --history real_tr            # 1988+ pool
python bootstrap.py --n-boot 1000 --history rf --maint-margin 0.10
pytest -q
```

Outputs: `output/bootstrap_rf.csv`, `output/bootstrap_realtr.csv`,
`output/bootstrap_margin_sweep.csv`.

## What is still not fixed

- **Single-country menu of shocks.** Block-bootstrapping US history recombines
  US crashes with US recoveries; it cannot manufacture a Japan-1990-style
  permanent impairment the US never had. A cross-country panel bootstrap
  (Dimson-Marsh-Staunton / Jordà-Schularick-Taylor) remains the right fix for
  the survivorship tail.
- **Option pricing** still uses ATM VIX (×1.2) with no volatility skew or
  term-structure correction, so OTM-put premiums are likely understated — the
  modest surviving tail benefit is, if anything, optimistic.
- The put-expiry-at-measurement-date convention in the path engine is unchanged.
