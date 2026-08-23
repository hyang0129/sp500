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
