# Recession stress test: $100k, 2 MES / 4 ZT / −2 ZN (2s10s steepener)

**Portfolio at current prices** (S&P 7,674; 2y 4.14%; 6.5y 4.51%; 10y 4.76%; bill 3.71%):

| | |
|---|---|
| MES notional | $76,744 = **0.77x** the account |
| ZT | +$38.01/bp × 4 = **+$152/bp** |
| ZN | −$55.80/bp × 2 short = **−$112/bp** |
| Net DV01 | **+$40/bp** |
| Margin | $14,400 = **14.4%** of the account |

Method: replay each recession's daily deltas (yields and equity) onto today's
levels. Three windows per recession — `pre` (12m before the NBER peak),
`during` (peak→trough), `cycle` (pre-start → trough+12m).

---

## Headline: recessions are *not* what hurts this book

| recession | 12m BEFORE | DURING | Δ2s10s during | worst DD (cycle) |
|---|---|---|---|---|
| 1980 Volcker I | +5% | **+37%** | +159bp | 38% |
| 1981-82 Volcker II | **−23%** | **+42%** | +129bp | **45%** |
| 1990-91 Gulf/S&L | +19% | +20% | +88bp | 9% |
| 2001 dot-com | +5% | +21% | +162bp | 26% |
| 2007-09 GFC | +25% | +4% | +160bp | 20% |
| 2020 COVID | +22% | +1% | +31bp | 20% |

**The portfolio made money in all six recessions.** The reason is structural:
a recession *is* the Fed cutting the front end, which steepens the curve — and
this book is long that steepening. Every `during` window shows the 2s10s
spread widening (+31 to +162bp).

**In the two modern crises the rates legs act as a near-perfect equity hedge:**

| | MES | ZT | ZN | net |
|---|---|---|---|---|
| GFC (during) | −$26,528 | +$40,209 | −$12,989 | **+4%** |
| COVID (during) | −$7,681 | +$18,614 | −$10,979 | **+1%** |

The steepener gains almost exactly offset the equity loss. That is not luck —
it is what a curve steepener is supposed to do in a recession.

## The one window that hurts: the pre-recession inversion

**1981-82 Volcker II, the 12 months *before* the recession (Jul 1980 → Jul 1981):
−23%, max drawdown 34%.** ZT loses **−$82,864** while the short ZN leg only
recovers +$45,821. The 2s10s spread flattens **−173bp**, bottoming at **−194bp
inverted** — the deepest inversion in the sample.

This is the only negative window in the entire study. Every other
pre-recession period was fine (+5% to +25%) because none of them inverted
anywhere near as deeply — the next-worst minimum spread is +0.26bp (1980) and
the rest are solidly positive.

**So the risk is not recession, and it is not the level of rates. It is
curve flattening/inversion, which arrives 12–24 months *before* the recession.**

## Especially Volcker: the continuous 1979 → 1984 path

Running both dips as one compounding path (rather than separate replays):

| | |
|---|---|
| Final equity | **$205,911 (2.06x)** |
| CAGR | 15.53% |
| **Max drawdown** | **37.7%** |
| Trough | **$74,455 on 1980-03-27** |
| Margin call | **NONE** (requirement $14,400) |
| Below the $100k start for | **only 54 days** (1980-02-21 → 1980-04-15) |

Attribution: MES +$50,202, cash +$33,282, ZT +$19,045, ZN +$3,383.

Worst months: **1980-02 −18.1%**, 1979-10 −15.9% (the Oct-1979 "Saturday Night
Massacre"), 1980-03 −14.8%, 1981-04 −10.0%, 1981-12 −9.6%.

The path is violent but survivable: a 38% drawdown into March 1980, then a
sharp recovery as rates collapsed in April–May 1980, choppy range-trading
through the second dip, and a strong 1982–83 finish.

## What actually breaks it

Scaling every leg by k on the continuous Volcker path:

| k | position | max DD | trough | margin call |
|---|---|---|---|---|
| 1 | 2 MES / 4 ZT / −2 ZN | 37.7% | $74,455 | none |
| 1.5 | 3 / 6 / −3 | 54.4% | $58,523 | none |
| 2 | 4 / 8 / −4 | 68.9% | $42,590 | none |
| **2.5** | **5 / 10 / −5** | **77.9%** | $32,177 | **1980-03-17** |
| 3 | 6 / 12 / −6 | 73.3% | $41,133 | 1980-03-06 |

**You have ~2.5x headroom.** Beyond that the account is margin-called at the
March-1980 spike — and being stopped out there means missing the 1982-83
recovery that makes the whole thing work. (Rows past k=2.5 breach *earlier*,
which mechanically preserves capital by halting trading sooner — they are
"stopped out early", not "safer".)

## Sensitivity: level mode

Replaying actual historical yield *levels* (so collateral earns the real 8–16%
Volcker cash rates) instead of deltas:

- Volcker II `pre` is **−24%** (vs −23%) — the core finding is unchanged.
- The two modern crises come in roughly flat rather than slightly positive:
  GFC −2%, COVID −1%.
- No margin calls anywhere.

## Caveats

1. **Fixed contract counts** — as equity grows the position shrinks
   proportionally, so risk declines through each window. A constant-risk book
   would look worse.
2. Each recession's `pre`/`during`/`cycle` rows are **separate replays**, each
   restarting at $100k and at today's levels; they are not additive. The
   continuous 1979→1984 run is the one compounding path.
3. Delta mode floors rates at 5bp; ZN is priced off its ~6.5y CTD (so this is
   a 2s/6.5s steepener in substance); quarterly roll at par; no
   commissions/slippage/CTD-switch; margin figures are assumptions
   (MES $2,400, ZT $1,300, ZN $2,200) and CME raised margins sharply in 1980 —
   `--margin-mult` tests that.
4. Equity dividends assumed 4.5%/yr (era-appropriate; today's S&P yields ~1.2%).

## Bottom line

This book is **structurally long recessions** — it profited in all six since
1976, and in the GFC and COVID the steepener almost exactly cancelled the
equity drawdown. Its single real vulnerability is the **deep pre-recession
inversion**, and only the Volcker episode delivered one severe enough to
matter: −23% over the 12 months to July 1981, inside a continuous 1979–84 path
that drew down 37.7% to $74,455 but never got margin-called and ended at 2.06x.
At 2.5x this size, that same path *does* margin-call you in March 1980.
