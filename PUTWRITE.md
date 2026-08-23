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
