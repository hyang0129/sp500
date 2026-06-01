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
### 5a. Fixing the ruin model: short-option margin + the 1929 crash

The first cut reported P(ruin)=0 for writers, which was an artifact of two
things. Both are now fixed, and the conclusion reverses.

**Fix 1 -- short-option margin** (`backtest.py`): a short put is now marked to
market against equity *and* carries its own maintenance margin on the put
notional, so a writer can actually be margin-called. Verified: a 1x+short-ATM
book (full notional) is wiped by the 1987 crash at a 25% requirement.

**Fix 2 -- crash clustering & the worst crash.** Block length (21/63/126-day)
barely moved the writer's ruin (`output/put_selling_margin.csv`) -- clustering
alone isn't the issue. The real issue is the *pool*: `history="rf"` starts in
**1934 and excludes the 1929-32 crash (-86%)**, the single worst event for a
put-seller. Putting it back (`history="all"`) is decisive
(`output/put_selling_depression.csv`):

20-year horizon, short ATM puts, ratio 1.0:

| pool | short-opt margin | median CAGR | tw_median | 5th-pct wealth | P(ruin) |
|---|---|---|---|---|---|
| 1934+ (no Depression) | 15% | 21.6% | 50.1x | 5.26x | 0.1% |
| **1928+ (incl. 1929-32)** | **15%** | 19.1% | 28.6x | **0.00x** | **7.2%** |
| 1928+ (incl. 1929-32) | 25% | 21.7% | 0.00x | 0.00x | **55.2%** |

The naked 1x holder rides the same Depression-inclusive scenarios to a 1.71x
5th-percentile (P(ruin)=0). The put-writer, on the same paths, has a **wiped-out
5th percentile (0.00x) and 7-55% ruin**. Selling puts converts a survivable-if-
painful left tail into a wipeout -- the textbook "pennies in front of a
steamroller." The median stays gorgeous (19-22%) right up until the tail event
zeroes it.

**Corrected verdict on put-writing.** The "improves everything" headline was the
joint product of (a) an assumed 20% VRP edge (fair pricing halves the median
gain and erases the tail gain, §5), (b) no short-option margin, and -- the big
one -- (c) a resampling pool that excluded the 1929-32 crash. Fix all three and
systematic full-notional ATM writing is a high-median, fat-left-tail short-vol
bet with real wipeout risk, not a free lunch. Lower ratios / further-OTM strikes
scale the risk down proportionally.

Reproduce: `python put_selling.py` (full grid); the margin/clustering and
Depression reruns are in `output/put_selling_margin.csv` and
`output/put_selling_depression.csv`.

## What is still not fixed

- **Single-country menu of shocks.** Block-bootstrapping US history recombines
  US crashes with US recoveries; it cannot manufacture a Japan-1990-style
  permanent impairment the US never had. A cross-country panel bootstrap
  (Dimson-Marsh-Staunton / Jordà-Schularick-Taylor) remains the right fix for
  the survivorship tail.
- **Option pricing** still uses ATM VIX (×1.2) with no volatility skew or
  term-structure correction, so OTM-put premiums are mispriced (long OTM puts
  understated; short-put VRP is a single flat markup).
- **The monthly path is additive intra-month**, which dampens the depth of a
  sharp single-month crash and so understates intra-month margin calls (a writer
  needs a ~35% one-month index drop to be called at 15% margin). A daily-marked
  path would call writers more often; the §5a ruin figures are still a floor.
- **Default `history="rf"` (1934+) excludes the 1929-32 crash.** Tail-sensitive
  work (esp. put-writing) should use `history="all"` (1928+); §5a shows it is
  decisive. Cross-country panels (DMS / Jordà-Schularick-Taylor) remain the fix
  for impairments the US never had at all (Japan-1990).
- The put-expiry-at-measurement-date convention in the path engine is unchanged.

Resolved since the first draft: short-option margin (§5a, writers can now be
margin-called) and crash-clustering sensitivity (block length 21/63/126 barely
moves results -- §5a).

### 5b. Position sizing is the whole game: put-writing by notional ratio

The §5a wipeout was a full-notional phenomenon. Sweeping the short-put notional
ratio (sell ATM 30-day puts, NEW short-option margin at 15%, Depression-inclusive
`all` pool, 20-year horizon; `output/put_selling_ratio.csv`):

| ratio | median CAGR | tw_median | 5th-pct wealth | P(ruin) |
|---|---|---|---|---|
| naked 1x | 10.1% | 6.8x | 1.71x | 0% |
| 0.25 | 12.5% | 10.5x | **2.12x** | 0% |
| 0.5 | 14.5% | 15.1x | 2.44x | 0% |
| 0.75 | 16.8% | 21.7x | 2.33x | 1.2% |
| 1.0 | 19.1% | 28.6x | **0.00x** | **7.2%** |

- At **ratio 0.25-0.5 the verdict is genuinely good**: median *and* 5th-percentile
  wealth both beat naked 1x, at zero ruin, even with 1929 in the pool. Premium
  collected every (mostly-calm) month compounds into a buffer that absorbs the
  small crash loss taken on a fraction of notional.
- **The cliff is between 0.5 and 1.0**, not in the strategy. 0.75 leaks a little
  ruin (1.2%); 1.0 overwhelms the buffer -> 5th-pct collapses to 0x, 7.2% ruin.
- Dose-response: each +0.25 ratio adds ~+2.3 pts median CAGR; free on the tail up
  to 0.5, toxic by 1.0. **Right-sizing (~0.25, up to ~0.5) is the conclusion** --
  the "pennies in front of a steamroller" failure was full-notional sizing.

## 6. What the VRP actually is — and a pricing correction

Measured from VIX vs the realized vol over the *next* 21 trading days (S&P 500,
1990-2026):

| measure | value |
|---|---|
| mean VIX (implied) | 19.5% |
| mean subsequent realized vol | 15.4% |
| IV - RV spread | +4.1 vol pts (median +4.7) |
| IV/RV | ~1.3x (ratio of means); ~1.4x (median of daily ratios) |
| variance premium VIX^2 - RV^2 | ~115 annualized variance pts |
| days IV > RV | 86% |

The premium is conditional (cushion widens from +2.8 vol pts when VIX<15 to +6.3
when VIX>30) and the ~14% of days where realized beats implied cluster in
crashes -- the VRP is **payment for crash risk, not free money**. OTM puts carry
an extra skew premium (their IV sits above VIX).

**Pricing correction.** The VRP is *already inside VIX*, and the sim prices with
sigma=VIX. So **`vrp_mode="fair"` (premium = BS at VIX) is the realistic
put-seller** -- selling at the market already harvests the full VRP because the
payout uses realized prices. `vrp_mode="marked_up"` (BS at 1.2xVIX ~ 1.55x
realized) over-credits ATM writers and was too generous in sections 5/5b above.
For ATM, fair is correct; for OTM, marked-up is a rough proxy for skew.

Realistic ATM put-writing (fair premium, Depression pool, 15% margin, 20y;
`output/put_selling_ratio_fair.csv`):

| ratio | median CAGR | 5th-pct wealth | MDD_p95 | P(ruin) |
|---|---|---|---|---|
| naked 1x | 10.1% | 1.71x | 70% | 0% |
| 0.25 | 11.1% | 1.66x | 75% | 0% |
| 0.5 | 12.0% | 1.51x | 81% | 0% |
| 0.75 | 12.6% | 1.15x | 87% | 1.2% |
| 1.0 | 13.5% | 0.00x | 100% | 7.4% |

- The harvestable edge is **~+1 pt CAGR per 0.25 notional** (a few pts/yr total),
  matching what CBOE PUTW-style indices earn over cash -- not the +2.4/+9 pts the
  marked-up run implied.
- Realistic put-writing does **NOT improve the tail** (5th-pct 1.66x at r0.25 vs
  naked 1.71x); it trades a fatter left tail + deeper drawdowns for a modest
  return bump. The earlier "improves the tail too" was the double-counted markup.
- Net: a sensible small-size (~0.25) return enhancer that is explicitly paid for
  bearing crash risk; ruinous at full notional.

## 7. Put-writing vs leverage, and OTM / delta-targeted strikes

Head-to-head on one basis (1928+ pool, 15% margin, block 63, realistic pricing:
fair=VIX base + linear skew 0.7 vol-pts per unit OTM; delta strikes via
`model.delta_strike`). `output/leverage_vs_putwrite.csv`,
`output/otm_delta_putwrite.csv`.

20-year, matched roughly by median CAGR:

| strategy | median CAGR | 5th-pct wealth | MDD_p95 | P(ruin) |
|---|---|---|---|---|
| naked 1x | 10.1% | 1.71x | 70% | 0% |
| 1.5x futures | 12.3% | 1.13x | 89% | 0.1% |
| 1.75x futures | 13.1% | 0.00x | 100% | 5.9% |
| sell ATM r0.5 | 12.0% | 1.51x | 81% | 0% |
| **sell 5%OTM r0.5** | 11.7% | **1.77x** | 77% | 0% |
| sell 10%OTM r0.5 | 11.1% | 1.78x | 74% | 0% |
| sell 25-delta r0.5 | 11.5% | 1.66x | 77% | 0% |
| sell 10-delta r0.5 | 11.0% | 1.71x | 75% | 0% |

- **Put-writing beats leverage on risk-adjusted terms.** At a matched ~12%
  median, 1.5x futures has a 1.13x tail / 89% drawdown; ATM r0.5 has 1.51x / 81%;
  5%OTM r0.5 has **1.77x / 77%**. Leverage amplifies the whole multi-year
  drawdown path and trips the margin cliff (1.75x futures wipes 5.9%); writing's
  per-period loss is bounded and the premium is compounding carry. (Caveat:
  futures often carry lower maintenance margin than short options; a 5-10%
  futures margin would narrow but not close the gap over 20y.)
- **OTM beats ATM for the writer.** Moving the strike out (5-10% OTM, or 10-25
  delta) trades a little median for a markedly better tail -- because moderate
  crashes don't reach the strike. At ratio 0.5, **5-10% OTM writing lifts the
  median above naked 1x AND keeps the 5th-percentile at/above naked (1.77-1.78x
  vs 1.71x)** even with skew pricing and 1929 in the pool -- the closest thing to
  a genuine both-ends improvement found in this study.
- **Delta-targeting** (`put_delta`) gives a vol-adaptive strike (25-delta ~ 3.4%
  OTM, 10-delta ~ 6.6% OTM at 1-month) and lands between the fixed-% results, as
  expected; its edge over fixed-% is regime-adaptivity, not visible in pooled
  stats. Lower delta = further OTM = better tail, less median.

**Best risk/reward overlay in the study:** moderate-size (~0.5), modestly-OTM
(~5-10% / 10-25 delta) put-writing -- it improves both the median and the tail
versus naked 1x, and dominates plain leverage at matched return. Sized to full
notional or struck ATM it gives back the tail; struck too far OTM it collects too
little. Conclusion rests on the skew assumption (slope 0.7) and the standing
caveats (single-country pool, additive intra-month path => ruin is a floor).
