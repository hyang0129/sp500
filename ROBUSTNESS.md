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

## 4. Leverage frontier — how much leverage, and where the ruin cliff is

`frontier.py` sweeps leverage on a fine grid (0.75× → 3×) with no puts, under a
realistic 10%-of-notional maintenance margin, over the 1934+ bootstrap. The
honest growth metric is **median terminal wealth** (it scores wipeouts as 0,
unlike median CAGR which is conditional on survivors). See
`output/leverage_frontier.{csv,png}`.

| L | 5y median wealth | 5y 5th-pct | 5y P(ruin) | 20y median wealth | 20y 5th-pct | 20y P(ruin) |
|---|---|---|---|---|---|---|
| 0.75× | 1.58× | 1.04× | 0% | 6.23× | 2.55× | 0% |
| 1.0× | 1.72× | 0.97× | 0% | 8.49× | 2.60× | 0% |
| 1.25× | 1.84× | 0.89× | 0% | 11.23× | 2.48× | 0% |
| 1.5× | 1.97× | 0.81× | 0% | 14.44× | 2.36× | 0% |
| 1.75× | 2.07× | 0.73× | 0% | 17.87× | 2.13× | 0% |
| **2.0×** | 2.16× | 0.65× | 0.1% | **21.18×** | 1.79× | 0% |
| 2.5× | 2.28× | **0.00×** | 5.7% | 17.10× | **0.00×** | 20.0% |
| 3.0× | 2.25× | 0.00× | 15.9% | **0.00×** | 0.00× | 53.8% |

Findings:

- **Geometric growth peaks at ~2× and then falls.** Over 20 years median wealth
  tops out at 2× (21×) and *declines* above it (2.5× → 17×, 3× → 0). Past 2×
  you are strictly dominated: less growth *and* a ruin cliff (ruin 0% → 20% →
  54% across 2.0 / 2.5 / 3.0×). 3× is not "aggressive", it is worse on every
  axis. So 2× is the rational ceiling, not a midpoint.
- **~1.5× is the risk-adjusted sweet spot.** At 20y it nearly doubles median
  wealth vs 1× (8.5× → 14.4×) while its 5th-percentile barely moves
  (2.60× → 2.36×, vs 2×'s 1.79×). The tail is almost flat from 0.75× to 1.5×
  because moderate-leverage drawdowns heal over two decades — extra growth there
  is close to free. The tail only starts paying around 1.75–2×.
- **Below 1× is pointless at long horizons.** At 20y, 1× beats 0.75× on *both*
  growth (8.5× vs 6.2×) and tail (2.60× vs 2.55×) — equity drift means
  de-levering below 1× just discards return. Sub-1× is only defensible for a
  short hold where keeping the worst case above 1.0× matters (0.75× / 5y: 1.04×).
- **The whole 1.25×–1.75× band** improves on 1×'s return while keeping a better
  5th-percentile than 2× — a continuous efficient region, with 1.5× at its knee.

Reproduce: `python frontier.py`.



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

## 5. Selling puts (put-writing overlay on 1x futures)

`put_selling.py`: 1x futures + SHORT 30-day cash-settled puts, strike
ATM/5%/10% OTM x notional ratio 0.25-1.0, bootstrap of 1934-2026, 10% margin.
Full grid in `output/put_selling.{csv,png}`; robustness in
`output/put_selling_robust.csv`. The marked-up headline ("selling puts improves
median, mean AND the tail") decomposes into two very different pieces:

ATM, ratio 1.0, 20-year horizon:

| condition | median CAGR | tw_median | 5th-pct wealth | MDD_p95 |
|---|---|---|---|---|
| naked 1x | 11.4% | 8.7x | 2.71x | 55% |
| short puts, marked-up (vol x1.2) | 21.2% | 46.7x | 6.74x | 71% |
| short puts, FAIR-priced | 15.8% | 18.7x | 2.75x | 76% |

- **Fair-priced put-writing is just added downside leverage, not alpha.** It
  still raises the median (11.4% -> 15.8%) because short puts add market
  exposure that earns the equity premium in an up-drifting market -- but the
  5th-percentile wealth is ~unchanged (2.75x vs naked 2.71x) and drawdowns
  deepen (55% -> 76%). The beta is available more cheaply via ~1.3x futures.
- **The entire tail *improvement* and about half the median uplift IS the
  assumed 20% VRP markup** (fair -> marked lifts tw_p5 2.75x -> 6.74x and median
  15.8% -> 21.2%). The attractive part of put-writing lives or dies on index
  puts actually being ~20% rich and that richness being harvestable net of cost.
- **The ruin numbers are NOT trustworthy for the short side.** P(ruin)=0 and the
  put_mtm_for_liquidation flag changing nothing are both artifacts: the margin
  threshold is sized to the 1x futures notional and charges no margin for the
  short-put exposure itself, so the model cannot margin-call a put-writer. A real
  broker margins short options (~15-20% of put notional + MTM loss); combined
  with the block bootstrap de-clustering crashes (it breaks up the back-to-back
  catastrophic months that bankrupt put-sellers), the true ruin risk of
  ratio-1.0 ATM writing is materially higher than shown. Building a proper
  short-option margin model is the prerequisite for trusting put-writing ruin.

Reproduce: `python put_selling.py` (full grid, marked-up + fair).
