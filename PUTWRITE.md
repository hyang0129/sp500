# Put selling on the S&P: delta, tenor, and the 1987 problem

Systematic short puts, strikes set by **target delta** (5 / 10 / 20), sized as a
multiple `w` of equity, `w` in {0, 0.25, 0.50, 0.75, 1.00}. Two structures:

- **hold** — write a 1-month put, hold to expiry, settle intrinsic
- **roll** — write a 2-month put, buy it back after 1 month

Options are priced off **VIX**, which already embeds the volatility risk
premium, so selling at VIX and settling against the realised path captures the
*actual historical* VRP rather than an assumed one. That is only honest where
VIX exists, so the study runs **1990-2026** (36y). October 1987 is handled as a
separate stress scenario. Margin follows the Reg-T/CBOE naked-put rule,
`max(20%*S - OTM, 10%*K) * units + premium`, checked against the daily
mark-to-market.

## 1. Cash + short puts (standalone)

| w | delta | 1M hold: CAGR / maxDD | 2M closed at 1M: CAGR / maxDD |
|---|---|---|---|
| 0.00 | — | 2.75% / 0.0% | 2.75% / 0.0% |
| 0.50 | 10d | 3.85% / 8.1% | 3.22% / 7.7% |
| 0.50 | 20d | 4.96% / 9.9% | 4.26% / 10.3% |
| 1.00 | 5d | 3.79% / 13.3% | 2.88% / 13.2% |
| 1.00 | 10d | 4.95% / 16.5% | 3.68% / 15.4% |
| **1.00** | **20d** | **7.17% / 20.4%** | 5.73% / 20.3% |

No liquidations anywhere in 1990-2026.

## 2. Hold to expiry beats closing early — in every single cell

Writing a 2-month put and closing it at 1 month **loses 0.2 to 1.4pp of CAGR**
versus writing a 1-month put and holding it. At 1x/10d: 4.95% vs 3.68%.

The reason is theta convexity. Option time value decays roughly with sqrt(T),
so the *final* month holds far more decay than the month before it. Writing 2M
and closing at 1M deliberately harvests the slow half of the decay curve and
hands the fast half back to the market. The 2M option does collect a larger
premium up front, but not enough to cover buying it back with a month of
expensive time value still in it.

**Verdict: 1-month, held to expiry.** The 2-month structure is dominated.

## 3. 20-delta dominates 5-delta on premium per unit of tail

| delta | CAGR over cash (1x) | Oct-1987 loss at expiry | premium per unit of catastrophe |
|---|---|---|---|
| 5d | +1.04pp | −14.4% | 0.072 |
| 10d | +2.20pp | −16.0% | 0.138 |
| **20d** | **+4.42pp** | −17.7% | **0.250** |

Far-OTM puts are the *worst*-priced part of the curve for a seller: 5-delta
takes essentially the same catastrophe risk as 20-delta (−14.4% vs −17.7% in
1987) for a quarter of the premium. **Selling 5-delta puts is a bad trade** —
you are picking up ~1pp a year and still get carried out in a real crash.

## 4. Layered on the 1.5x core — it actually earns its keep

Unlike the 2s10s steepener overlay (see INVERSIONS.md), put selling is genuinely
additive on a drawdown-adjusted basis. Same 1990-2026 path:

| config | CAGR | maxDD | worst intra-month | CAGR/DD |
|---|---|---|---|---|
| 1.5x plain | 18.07% | 69.1% | −43.8% | 0.262 |
| 1.75x plain | 20.18% | 75.5% | −51.1% | 0.267 |
| 2.0x plain | 22.12% | 80.8% | −58.4% | 0.274 |
| 2.5x plain | 25.46% | 88.6% | −73.0% | 0.287 |
| 1.5x + 0.5x 20d | 20.22% | 71.6% | −53.6% | 0.282 |
| **1.5x + 1x 20d** | **22.32%** | **74.1%** | −63.4% | **0.301** |

**1.5x + 1x 20-delta beats 2.0x plain on both axes** — higher CAGR (22.32% vs
22.12%) *and* lower max drawdown (74.1% vs 80.8%). Every put-write config has a
better CAGR/DD than every plain-leverage config. This is the opposite of the
steepener result.

## 5. But the tail is short-gamma, and 1987 is the counter-example

Worst *intra-month* mark deteriorates monotonically with the overlay: −43.8%
(plain 1.5x) to −63.4% (with 1x/20d). Max drawdown improves because the premium
keeps arriving and the position re-strikes further OTM after a vol spike — but
the single-month hit gets sharper. Short gamma trades drawdown depth for
drawdown speed.

**October 1987**, written 10/01, 1-month, held to expiry (realised vol ×1.15
used for the seller's premium, since no VIX quote exists):

| delta | strike | % OTM | premium | loss at expiry | peak MTM loss |
|---|---|---|---|---|---|
| 5d | 303.38 | −7.3% | 0.11% | **−14.4%** | −23.9% |
| 10d | 308.88 | −5.6% | 0.24% | **−16.0%** | −25.4% |
| 20d | 315.67 | −3.6% | 0.56% | **−17.7%** | −27.2% |

Per 1.0x of short-put notional; scales linearly with `w`. The index fell 31.3%
intra-month and closed the cycle down 21.9%.

That lands **on top of** the core's loss. A 1.5x core lost ~45% intra-month in
October 1987; add 1x/20d short puts at −27.2% peak and you are down roughly 70%
in a single month, facing a margin requirement that exploded with vol. The
1990-2026 sample shows zero liquidations precisely because it contains no
1987-scale event.

## Bottom line

- **1-month held to expiry, 20-delta.** The 2-month-closed-early structure is
  dominated in every cell; 5-delta is dominated on premium per unit of tail.
- **Sizing is the real decision.** At `w` = 0.5 on a 1.5x core you get +1.1pp of
  CAGR for essentially no change in max drawdown (69.0% vs 69.1%). At `w` = 1.0
  you get +2.2pp but the worst intra-month goes from −43.8% to −59.9%.
- **`w` = 0.5, 20-delta, 1-month held to expiry** is the configuration that adds
  return without materially changing the drawdown profile: 20.22% CAGR at 71.6%
  maxDD, versus 18.07% / 69.1% unoverlaid.
- Anything at `w` = 1.0 is a bet that no 1987 recurs. The premium is ~6.7%/yr at
  20-delta and one 1987 costs ~17.7% at expiry — about 2.6 years of premium — but
  the −27% peak mark is what triggers the margin call that ends the account.

## Caveats

- 1990-2026 only (VIX era). No 1987, no 1929. The single most important stress
  for a put seller is outside the sample and had to be modelled separately.
- European-style, cash-settled, no early assignment; no commissions, no bid-ask
  (real short-put spreads are wide in the tails, which hurts 5-delta most of all).
- One tranche at a time, written at month start — no laddering across strikes or
  expiries, which would smooth the path.
- Margin uses the static Reg-T rule; real SPAN margin rises with vol, so a crash
  would force liquidation *earlier* than modelled.
- Pricing uses VIX (a 30-day ATM-ish measure) for every strike, so it ignores the
  volatility **skew**. Real 5- and 10-delta puts trade at materially higher
  implied vol than ATM, so their true premium is higher than modelled — this
  understates the far-OTM seller's income and is the main reason to treat the
  5d-vs-20d ranking as directional rather than exact.

---

# Update: the real skew, measured — and an engine validation that failed

The caveat above ("pricing uses VIX for every strike, so it ignores skew") turned
out to matter more than flagged, and in **both** directions. Two new data series
settle it: **^SKEW** (CBOE SKEW index, 1990-2026) and **^PUT** (the real,
published CBOE S&P 500 PutWrite Index, 1996-2026).

## 1. The engine was wrong, and ^PUT caught it

^PUT sells **at-the-money** 1-month SPX puts fully collateralised — struck ATM,
so it is almost unaffected by skew. That makes it a clean test of the mechanics.

| | CAGR | vol | maxDD |
|---|---|---|---|
| ^PUT (actual) | **8.51%** | 15.2% | 37.1% |
| my engine, flat-VIX ATM | **13.19%** | 13.9% | 34.9% |
| difference | **+4.68pp** | −1.4pp | −2.2pp |

Daily return correlation 0.837, annual 0.913 — the *shape* was right, the
*level* was far too generous. Cause: **VIX is a variance-swap measure that
integrates across strikes, so a skewed surface puts VIX materially above true
ATM implied vol.** Selling an ATM put at VIX collects premium that does not
exist.

Calibrating `ATM IV = VIX - offset` against ^PUT:

| offset | engine CAGR | error vs ^PUT |
|---|---|---|
| 0.0p | 13.14% | +4.63pp |
| 2.0p | 10.06% | +1.55pp |
| **3.0p** | **8.55%** | **+0.04pp** |
| 4.0p | 7.06% | −1.45pp |

**3.0 vol points** reproduces the real index. (Pure VIX-minus-ATM is usually
1-2 points; the remainder absorbs bid-ask, commissions and roll-date differences
against the real index — so treat 3.0p as a total friction calibration, not a
pure surface measurement.)

## 2. What the real skew actually looks like

SKEW = 100 − 10·g1, with g1 the risk-neutral skewness of the 30-day return.

| statistic | value |
|---|---|
| SKEW median | 119.8 |
| SKEW p5 / p95 | 109.9 / 147.0 |
| SKEW max | 183.1 (2025-02-18) |
| g1 median | **−1.98** |
| corr(SKEW, VIX) | **−0.17** |

**SKEW is not VIX.** They are essentially uncorrelated (−0.17) — skew tends to
be *high when VIX is low*, which is complacency plus persistent tail-hedging
demand. And it has risen structurally:

| decade | median SKEW |
|---|---|
| 1990s | 115.3 |
| 2000s | 116.0 |
| 2010s | 124.8 |
| **2020s** | **139.9** |

Translated into vol points above ATM for 1-month SPX (Backus-Foresi-Wu first
order, dIV/d ln(K/F) = −g1/(6√T)):

| regime | SKEW | 20d | 10d | 5d |
|---|---|---|---|---|
| calm (p5) | 109.9 | +2.5p | +3.8p | +4.9p |
| **median** | 119.8 | **+5.0p** | **+7.6p** | **+9.8p** |
| stressed (p95) | 147.0 | +11.9p | +18.1p | +23.2p |
| extreme (max) | 183.1 | +21.0p | +32.0p | +41.0p |

The median row (10d at ATM+7.6p) sits squarely inside the market rule of thumb
of +5 to +8 points, so the mapping is sane at typical SKEW. It **overshoots at
extreme SKEW** — +41 points at 5-delta is not a real market — because the
expansion is first-order.

## 3. The error flips sign across the surface

With ATM = VIX − 3p plus the median smile, at VIX = 18:

| delta | strike | IV sold | vs flat-VIX (18.0%) |
|---|---|---|---|
| 50d (ATM) | +0.3% | 15.0% | **3.0p cheaper** |
| 20d | −4.4% | 20.2% | 2.2p richer |
| 10d | −8.5% | 25.1% | 7.1p richer |
| 5d | −13.3% | 31.3% | **13.3p richer** |

So the flat-VIX model **overstated** ATM premium and **understated** far-OTM
premium — the two errors run in opposite directions, crossing over around
25-delta.

## 4. Corrected results (1x notional, cash-collateralised, 1990-2026)

| delta | structure | flat-VIX CAGR | **calibrated-skew CAGR** | maxDD | worst intra-month |
|---|---|---|---|---|---|
| 5d | hold | 3.79% | **5.79%** | 5.2% | −5.2% |
| 5d | roll | 2.88% | 5.15% | 5.4% | −4.0% |
| 10d | hold | 4.95% | **8.28%** | 10.8% | −10.4% |
| 10d | roll | 3.68% | 6.56% | 10.3% | −8.0% |
| 20d | hold | 7.17% | **10.60%** | 18.7% | −16.1% |
| 20d | roll | 5.73% | 6.92% | 17.1% | −13.7% |

Cash baseline 2.75%.

**Hold-to-expiry still beats close-early in every cell**, and by a wider margin
(20d: 10.60% vs 6.92%). That conclusion strengthens.

## 5. The "5-delta is a bad trade" claim was too strong

| delta | edge over cash, flat-VIX | edge, calibrated skew | Oct-1987 loss | edge per unit of 1987 |
|---|---|---|---|---|
| 5d | +1.04pp | **+3.04pp** | −14.4% | 0.211 |
| 10d | +2.20pp | **+5.53pp** | −16.0% | 0.345 |
| 20d | +4.42pp | **+7.84pp** | −17.7% | **0.443** |

Skew nearly **triples** the 5-delta edge (1.04 → 3.04pp). 20-delta still wins on
catastrophe-adjusted efficiency (0.443 vs 0.211), so the ranking does not flip —
but the gap narrows from 3.5x to 2.1x, and 5-delta becomes a genuinely viable
trade rather than a near-pointless one.

And on **normal-times** drawdown the ranking actually inverts:

| delta | edge over cash | maxDD | edge per unit of maxDD |
|---|---|---|---|
| **5d** | +3.04pp | 5.2% | **0.58** |
| 10d | +5.53pp | 10.8% | 0.51 |
| 20d | +7.84pp | 18.7% | 0.42 |

The two metrics disagree, and the disagreement is the real insight: **5-delta is
the most efficient use of ordinary drawdown, 20-delta the most efficient use of
catastrophe risk.** In a 1987-style gap the market fell 31.3% and blew through
both strikes, so being 13% OTM instead of 4% OTM bought far less protection than
the everyday risk profile suggests.

## 6. Revised recommendation

- The **structure** conclusion is unchanged and now stronger: **1-month, held to
  expiry**.
- The **strike** conclusion softens. 20-delta remains the best use of tail risk,
  but 5- and 10-delta are far more attractive than the flat-VIX model implied,
  and 5-delta has by far the gentlest ordinary drawdown (5.2% vs 18.7%).
- **Everything sized off the flat-VIX numbers in the section above was ~3pp/yr
  too optimistic at ATM.** The calibrated model is the one to size against.

## Remaining caveats on the skew work

- The BFW slope is first-order and overshoots at extreme SKEW; results at the
  p95+ tail of the SKEW distribution should be treated as indicative.
- The 3.0p offset is a *total friction* calibration against ^PUT, not a pure
  measurement of the VIX-ATM gap.
- The smile is linear in log-moneyness and downside-only; real surfaces curve.
- SKEW is a 30-day measure applied to the 2-month leg as well.
- ^PUT itself sells ATM, so it validates the ATM level and the mechanics — it
  does **not** independently validate the OTM smile slope.

---

# Update: weekly vs monthly expiry

Generalised the engine to write on any cycle. **There is no ^WPUT history on
the source (one day only), so unlike the monthly case the weekly result has no
external index to validate against** — it is model output, not a replication.

## Why weekly should collect more

Premium scales with sigma*sqrt(T), so annualised premium at the same delta is

    52*sqrt(1/52) / (12*sqrt(1/12)) = sqrt(52/12) = 2.08x

Measured in the engine: **2.27x** the gross premium (the extra is smile).
Confirmed not to be a modelling artifact: the smile slope goes as 1/sqrt(T)
while log-moneyness goes as sqrt(T), so the **vol-point uplift at a given delta
is tenor-invariant** (10d: +10.1p monthly, +10.6p weekly). There is a regression
test pinning this.

But the same delta sits far closer to spot: at 18 vol a 10-delta put is
**6.1% OTM monthly and 3.1% OTM weekly**, and the payout ratio reflects it —
weekly pays out **70% of premium collected versus monthly's 41%**.

## Results, 1x notional, cash-collateralised, calibrated skew, 1990-2026

Transaction cost is charged on every option traded as a fraction of its value
(half-spread plus commission).

| cycle | delta | struct | 0% cost | 10% cost | 25% cost | maxDD | worst intra-month |
|---|---|---|---|---|---|---|---|
| month | 10d | hold | 8.28% | 7.68% | 6.79% | 10.8% | −10.4% |
| month | 20d | hold | 10.60% | 9.51% | 7.90% | 18.7% | −16.1% |
| month | 20d | roll | 6.92% | 4.37% | 0.66% | 17.1% | −13.7% |
| **week** | 5d | hold | 8.61% | 7.95% | 6.97% | **4.9%** | −4.8% |
| **week** | 10d | hold | **13.29%** | 11.97% | 10.03% | 7.1% | −7.1% |
| **week** | 20d | hold | **17.20%** | 14.79% | **11.26%** | 12.4% | −10.5% |
| week | 20d | roll | 10.43% | 4.85% | **−3.01%** | 12.5% | −8.6% |

Cash baseline 2.75%.

**In-sample weekly wins on both axes** — 20d hold returns 17.20% vs 10.60% with
a *lower* max drawdown (12.4% vs 18.7%). Even at a punitive 25% cost it still
leads, 11.26% vs 7.90%.

The mechanism is re-striking speed. A monthly writer carries a stale strike
through the whole month; a weekly writer re-strikes every Monday at the new spot
and the new (higher) vol, so it adapts to a selloff four times faster.

**Hold-to-expiry still beats close-early, and costs make it brutal.** The weekly
"roll" structure trades twice as often and pays both ways: at 25% cost it goes
**negative** (−3.01%). Closing early is the worst idea in the study.

## But October 1987 reverses it

Same 1x notional, run through Jun-Dec 1987 (no VIX, so trailing realised vol):

| cycle | delta | final | maxDD |
|---|---|---|---|
| month | 5d | 0.956 | 18.0% |
| month | 10d | 0.921 | 22.5% |
| month | 20d | **0.913** | 26.2% |
| week | 5d | 0.859 | 19.8% |
| week | 10d | 0.834 | 23.8% |
| week | 20d | **0.837** | **29.2%** |

**Weekly loses roughly 8pp more than monthly through 1987.** The crash was a
staircase, not a single gap:

    Oct 02  328.07
    Oct 09  311.07
    Oct 16  282.70
    Oct 23  248.22

The weekly writer was hit **four consecutive times**, re-striking each Monday at
a level that then fell again. The monthly writer took one hit. Faster
re-striking is an advantage into a V-shaped shock and a liability in a sustained
multi-week decline — it hands you a fresh short strike every week on the way
down.

That is exactly why the 1990-2026 sample flatters weekly: COVID, 2018 and 2011
were sharp single-event shocks, which is weekly's best case.

## Verdict

- **Weekly, 20-delta, held to expiry** is the highest-returning configuration
  tested and, in-sample, also the lowest-drawdown one at its return level.
- **Never close early**, on any cycle. At realistic costs the weekly roll is
  the only configuration in the entire study that loses money.
- **The weekly edge is conditional on crash shape.** It beats monthly in
  V-shaped shocks and loses to it in staircase declines. 1987 is the only
  staircase in the record and weekly lost ~8pp there.
- Weekly's advantage also rests on 52 fills a year at reasonable spreads. The
  cost columns show it survives 25%, but that assumes you can actually transact
  a 20-delta SPXW weekly at something near mid, every week, at size.

## Extra caveats specific to the weekly work

- **No ^WPUT index history to validate against** — the monthly case was
  anchored to the real ^PUT index, the weekly case is not anchored to anything.
- The CBOE SKEW index is a **30-day** measure; applying it to a 7-day option
  extrapolates. Real 1-week skew is steeper still than the sqrt(T) scaling
  implies, which if anything understates weekly premium.
- Weekly gamma near expiry is far larger than a daily-marked model captures;
  a Friday-to-Monday gap through a near strike is the dominant real-world risk
  and is only crudely represented here.
- SPX weeklys did not exist before ~2005, so the 1990-2005 portion of the weekly
  backtest is counterfactual — the instrument was not tradable.

---

# Update: roll mechanics — and my weekly model had the worst possible schedule

The weekly results above wrote **Monday, expiring the following Monday**. Real
SPXW weeklies expire **Friday**, so that schedule was not tradable for most of
the sample, and — it turns out — it is the single worst way to arrange the
exposure.

## The weekend is where the tail lives

| weekday | n | sd | worst day |
|---|---|---|---|
| **Mon** | 2382 | **1.25%** | **−20.46%** |
| Tue | 2583 | 1.09% | −5.74% |
| Wed | 2584 | 1.05% | −9.03% |
| Thu | 2534 | 1.08% | −9.49% |
| Fri | 2519 | 1.03% | −6.76% |

**9 of the 20 worst days since 1976 are Mondays — 45%, against a 19% base
rate.** Monday carries 24.5% of all realised variance. The four worst days in
the record are all Mondays: 1987-10-19 (−20.46%), 2020-03-16 (−11.98%),
2008-09-29 (−8.79%), 2011-08-08 (−6.65%).

For a short-put book the weekend gap is not a detail. It is the risk.

## Three tradable schedules

| schedule | tenor | weekend | where the weekend falls |
|---|---|---|---|
| `mon_mon` | 7 cal days | carried | **at expiry** — maximum gamma, no time value left |
| `fri_fri` | 7 cal days | carried | **at inception** — far OTM, full time value |
| `mon_fri` | 4 cal days | **none** | flat Fri close → Mon |

## In-sample (1x notional, calibrated skew, 1990-2026)

| schedule | delta | 0% cost | 10% | 25% | maxDD | worst IM |
|---|---|---|---|---|---|---|
| monthly | 20d | 10.60% | 9.51% | 7.90% | 18.7% | −16.1% |
| mon_mon | 20d | 17.20% | 14.79% | 11.26% | **12.4%** | −10.5% |
| **fri_fri** | 20d | **17.99%** | **15.60%** | **12.11%** | 17.6% | −15.4% |
| mon_fri | 20d | 11.07% | 9.34% | 6.79% | 19.2% | −14.6% |

`fri_fri` returns most; `mon_fri` gives up roughly a third of the return
because it only covers ~57% of the calendar.

## October 1987 inverts the ranking completely

| schedule | 20d final | maxDD |
|---|---|---|
| monthly | 0.913 | 26.2% |
| **mon_mon** | **0.837** | **29.2%** |
| fri_fri | 0.967 | 24.6% |
| **mon_fri** | **1.009** | **11.7%** |

`mon_mon` — the schedule the earlier weekly results used — is the **worst** of
the four, because Black Monday landed on its expiry, where gamma is maximal and
there is no time value to absorb the move. `fri_fri` carries the identical
weekend but at inception, when the option is far OTM with full time value, and
loses less than half as much. `mon_fri` sidesteps it entirely.

**So the earlier "weekly beats monthly" headline was measured on the worst
schedule, and it still won in-sample — but its 1987 loss was an artifact of
that schedule, not of weekly writing as such.** On `fri_fri`, weekly beats
monthly in-sample *and* survives 1987 better (0.967 vs 0.913).

## An important honest caveat on the 1987 mon_fri number

The engine trades at the **close**. So the `mon_fri` writer on Monday 1987-10-19
writes at 224.84, having sat out the entire day — not merely the overnight gap.
Black Monday was largely an *intraday* decline, so a real Monday-morning writer
would have caught most of it. **The 1.009 figure is therefore too flattering**;
the genuine benefit is avoiding the Friday-close-to-Monday-open gap, which is a
part of that day's move, not all of it.

## On the practical roll, which is what prompted this

- `fri_fri` as modelled settles the expiring option and writes the new one at
  the same Friday close. SPXW is PM-settled at that close, so in practice you
  write minutes before it — a few minutes of overlap or of gap, second-order.
- Rolling at Friday **open or midday** means buying back the expiring option
  with hours of life left. That is the `roll` structure, and it is the most
  expensive thing in this study: you surrender the fastest-decaying hours *and*
  pay the spread twice. At 25% cost the weekly roll returns **−3.01%**.
- Deliberate **double exposure** (writing next week's before this week's
  expires) doubles notional for the overlap. Over a weekend that is the exact
  window where the tail lives, so it is the worst possible time to be doubled.

## Revised verdict on tenor

- **`fri_fri` weekly, 20-delta, held to expiry** is the best of the schedules
  tested — highest return in-sample and better 1987 survival than monthly.
- **Never `mon_mon`.** Putting the weekend at expiry is strictly worse than
  putting it at inception, for the same tenor and the same delta.
- **`mon_fri` is the defensive choice**: roughly monthly-level returns (11.07%
  vs 10.60%) with materially the best crash behaviour, at the cost of 52 trades
  a year instead of 12 and no exposure 43% of the time.
- All of this remains unvalidated against any published weekly index, and the
  pre-2005 portion is counterfactual because SPX weeklys did not exist.

---

# Update: can you actually write at PM settlement? And does the roll day matter?

## The mechanical answer: nearly, but not exactly

SPXW weeklies are **PM-settled**: the settlement value is the S&P 500 *closing*
level on expiry Friday, and the expiring series stops trading at 16:00 ET.
Non-expiring SPX/SPXW series keep trading until 16:15 ET.

So a continuous roll is *almost* available, three ways, none of them exact:

1. **Write next week's in the 16:00-16:15 window**, after the expiring one has
   stopped trading. Closest to true continuity — but the official settlement
   print is not instant (it is built from all 500 components' closing prices),
   and liquidity in that quarter-hour is thin.
2. **Write next week's a few minutes before 16:00**, while the expiring one is
   still alive. This is what most programs do. You are briefly double-exposed,
   but only for minutes during which the cash index is barely moving — the
   overlap is not a weekend, so it is nearly harmless.
3. **Write next week's after the weekend.** Genuinely flat over the gap; that is
   the `mon_fri` schedule, and it costs about a third of the return.

You cannot transact *at* the settlement price itself — that is a calculated
print, not a tradable level. The engine assumes a fill at the close, which is a
few minutes and a half-spread optimistic, no more.

## But the roll-day question swamps it

Scanning the weekday while holding everything else fixed (20-delta, 1x,
calibrated skew, 1990-2026):

| span | weekend falls | CAGR 0% | CAGR 10% | maxDD | worst IM | 1987 final |
|---|---|---|---|---|---|---|
| mon_mon | **at expiry** | 17.20% | 14.79% | **12.4%** | −10.5% | **0.837** |
| tue_tue | mid-life | **18.36%** | **15.95%** | 13.0% | −12.3% | 0.916 |
| wed_wed | mid-life | 18.12% | 15.73% | 15.5% | −12.2% | 0.978 |
| thu_thu | mid-life | 17.99% | 15.59% | 22.3% | −14.8% | **0.979** |
| fri_fri | at inception | 17.99% | 15.60% | 17.6% | −15.4% | 0.967 |
| mon_fri | none | 11.07% | 9.34% | 19.2% | −14.6% | **1.009** |
| *monthly* | — | *10.60%* | *9.51%* | *18.7%* | *−16.1%* | *0.913* |

**The five 7-day roll days span just 1.16pp of CAGR (17.20-18.36%).** Weekly
beats monthly by ~7pp on *every* one of them, so that conclusion is robust. But
the differences *between* roll days are small, and `tue_tue` topping the table
has no mechanism behind it — that is noise.

**This corrects the previous update.** I reported `fri_fri` (17.99%) beating
`mon_mon` (17.20%) and attributed it to weekend-at-inception versus
weekend-at-expiry. With the holiday bug fixed, `fri_fri` ties `thu_thu` and
sits mid-pack, below `tue_tue`. A 0.8pp gap inside a 1.16pp noise band does not
support a mechanism. **Do not choose the roll day on these numbers.**

What *does* survive:

- **`mon_mon` is genuinely the worst on return (17.20%) and by far the worst in
  1987 (0.837 vs 0.916-0.979 for every other day).** Weekend-at-expiry is a real
  liability — that part holds.
- **`mon_fri` is genuinely different in kind**, not degree: about a third less
  return for the best crash behaviour in the set (1987 final 1.009).
- Interestingly `mon_mon` has the *lowest* in-sample maxDD (12.4%) while having
  the worst 1987 — an in-sample statistic pointing the opposite way from the
  out-of-sample stress. A good reminder that 1990-2026 max-drawdown is not a
  tail measure.

## Bug fixed in this pass

The generalised roll calendar initially skipped any week whose nominal expiry
weekday was a holiday, which left the previous week's option open for a
fortnight while still priced as a one-week option (`fri_fri` lost 65 of 1910
expiries). It now falls back to the last session of that week, which is what the
exchange does. All six schedules now write 52.2 times a year. Two regression
tests added: no week may be skipped, and the roll-day spread must stay inside
2pp.

---

# Update: most of that roll-day scan was not tradable

Verified against Cboe's own announcements. SPXW expiry weekdays were listed at
very different times:

| expiry weekday | first listed | years available to 2026 | share of the 36.6y backtest that is counterfactual |
|---|---|---|---|
| **Friday** | 2005-10-28 | 20.8 | 43% |
| Wednesday | 2016-02-23 | 10.5 | 71% |
| Monday | 2016-08-15 | 10.0 | 73% |
| **Tuesday** | **2022-04-18** | **4.3** | **88%** |
| **Thursday** | **2022-05-11** | **4.3** | **88%** |

So `tue_tue` "winning" the previous scan at 18.36% was computed on a contract
that **did not exist for 88% of the sample**. The same applies, less severely,
to `mon_mon` and `wed_wed`. Only the Friday schedules have real history, and
even they start in late 2005.

## On the common window when all five actually existed (2022-05-11 →)

| span | CAGR | maxDD | worst IM |
|---|---|---|---|
| mon_mon | 32.91% | 5.1% | −4.4% |
| **tue_tue** | **32.52%** | 6.4% | −6.0% |
| wed_wed | 34.62% | 6.4% | −6.2% |
| **thu_thu** | **36.16%** | 4.9% | −4.4% |
| fri_fri | 34.74% | 4.6% | −4.3% |
| mon_fri | 24.11% | 5.2% | −4.6% |
| *monthly* | *18.92%* | — | — |

**The ranking completely reshuffles.** `tue_tue` goes from best on the full
counterfactual sample to **worst** here; `thu_thu` goes from mid-pack to best.
A ranking that inverts between samples is noise, and the roll day should not be
chosen on it — which is now settled for a much stronger reason than before.

Note also how flattering 2022-2026 is: monthly writing returns **18.92%** on
that window against **10.60%** over 1990-2026. Post-COVID vol normalisation plus
a strong bull market is close to the best regime a put seller can have. None of
the common-window numbers should be read as expectations.

## The one genuinely tradable weekly-vs-monthly test

Friday weeklys, 2005-10-28 → 2026, 20-delta, 1x, calibrated skew:

| book | CAGR | maxDD | worst IM |
|---|---|---|---|
| monthly | 10.29% | 18.7% | −16.1% |
| monthly @10% cost | 9.08% | 19.1% | −16.1% |
| **weekly fri_fri** | **19.34%** | 17.6% | −15.4% |
| **weekly fri_fri @10% cost** | **16.64%** | 18.1% | −15.5% |
| weekly mon_fri | 12.56% | 19.2% | −14.6% |
| weekly mon_fri @10% cost | 10.59% | 20.9% | −14.9% |

Cash over the same window: 1.72%.

**The weekly-beats-monthly conclusion survives the tradability filter** — on the
only schedule with real history, and at a realistic cost, weekly returns 16.64%
against monthly's 9.08%, with a slightly *lower* max drawdown.

## Revised verdict

- **Friday weeklys are the answer** — not because they tested best (they did
  not; `thu_thu` did on the common window), but because they are the only weekly
  schedule with meaningful history and the deepest liquidity.
- **Ignore the roll-day ranking entirely.** It inverts between samples, and four
  of the five weekdays are recent listings.
- Weekly still beats monthly by ~7.5pp on the tradable window at 10% cost.
- Everything before 2005-10-28 in any weekly result is counterfactual and should
  be read as a simulation of an instrument that did not exist.

`SPXW_LISTED` and `listed_from()` now record these dates in code, with a test,
so a future run cannot silently backtest a contract before it was listed.

Sources: [Cboe: Tuesday and Thursday SPX
Weeklys](https://ir.cboe.com/news/news-details/2022/Cboe-to-Add-Tuesday-and-Thursday-Expirations-for-SPX-Weeklys-Options-04-13-2022/default.aspx),
[Cboe: Monday-expiring
Weeklys](https://ir.cboe.com/news/news-details/2016/CBOE-to-List-SPX-Monday-Expiring-Weeklys-Options-07-11-2016/default.aspx),
[Cboe: Wednesday-expiring
Weeklys](https://ir.cboe.com/news/news-details/2016/CBOE-to-List-SPX-Wednesday-Expiring-Weeklys-Options-02-01-2016/default.aspx).
