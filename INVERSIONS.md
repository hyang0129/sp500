# Flattening screen: does the 2s10s steepener overlay earn its keep?

Screens all of 1976–2026 for the worst curve-flattening episodes **regardless of
whether a recession followed** (1994 and 2022-23 both inverted hard without a
Volcker outcome), and compares:

| book | position |
|---|---|
| **full** | 2 MES + 4 ZT − 2 ZN |
| **equity** | 2 MES only |
| **rates** | 4 ZT − 2 ZN only |

$100k account, delta replay onto today's levels.

## Context: the real 2s10s record

Range since 1976: **−239bp (1980-03-07)** to **+329bp (2008-11-03)**.
Inverted in 1978-82, 1989-90, 2000, 2006-07, 2019, and **2022-24** (−103bp in
2023, the deepest since Volcker).

---

## Finding 1: the overlay loses in **8 of 8** flattening episodes

| episode ends | Δ2s10s | 2 MES only | full book | **overlay cost** |
|---|---|---|---|---|
| 1978-12 | −152bp | +8.4% | −13.1% | −21pp |
| **1980-03** | −176bp | +13.0% | −23.2% | **−36pp** |
| **1981-05** | −235bp | +22.9% | −14.9% | **−38pp** |
| 1989-03 | −178bp | +16.0% | −5.5% | −22pp |
| 1994-12 | −165bp | +4.1% | −15.7% | −20pp |
| 2005-06 | −183bp | +8.8% | −11.1% | −20pp |
| 2012-07 | −154bp | +5.1% | −5.6% | −11pp |
| **2022-11** | −181bp | −7.4% | **−32.5%** | −25pp |

Average cost ≈ **−24pp**. Not one exception.

**The single worst episode is 2022, not Volcker.** −32.5% with a 37.4% drawdown.
In 1980-81 the equity leg was *up* double digits and cushioned the rates loss;
in 2022 stocks fell *and* the curve flattened, so both legs lost together. That
is the genuine tail: the diversification fails exactly when you need it.

In the 12 months *after* each flattening the overlay usually wins back ground
(+22pp after 1980, +31pp after 1981) — but not always (−8pp in 1978, −8pp in
2005, −0.4pp in 2022).

## Finding 2: but in recessions it is a real equity hedge

| recession (during) | 2 MES only | full book | overlay edge |
|---|---|---|---|
| 1980 | +14.0% | +37.0% | +23pp |
| 1981-82 | +10.2% | +42.4% | +32pp |
| 1990-91 | +6.2% | +20.4% | +14pp |
| 2001 | −3.4% | +21.2% | +25pp |
| **2007-09 GFC** | **−24.0%** | **+3.5%** | **+27pp** |
| 2020 COVID | −7.1% | +0.6% | +8pp |

Average **+21pp**, and it turns the GFC from −24.0% into +3.5% while halving the
drawdown (38.8% → 21.1%). This is a genuine, repeatable hedge — the overlay is
doing exactly what a steepener should when the Fed cuts.

## Finding 3: risk-adjusted, plain MES wins — decisively

180 rolling 5-year windows, 1976–2026:

| book | median | 5th pct | worst | median DD | worst DD | ret/DD |
|---|---|---|---|---|---|---|
| **full** (2 MES + overlay) | +83.7% | +10.9% | −25.5% | 21.4% | **56.9%** | **3.91** |
| MES only 2x | +77.0% | +9.7% | **−1.2%** | 16.4% | 39.7% | **4.70** |
| **MES only 3x** | **+105.7%** | +6.6% | −12.1% | 23.5% | 59.0% | 4.50 |
| MES only 4x | +134.0% | +6.1% | −27.2% | 30.8% | 77.5% | 4.36 |

**At matched risk the overlay is dominated.** The full book carries a 21.4%
median drawdown for a +83.7% median return; plain **3x MES** carries a
comparable 23.5% drawdown for **+105.7%** — about 22pp better. The full book has
the *worst* return-per-drawdown of all four.

Same verdict on the continuous Volcker path (1979→1984):

| book | max DD | final |
|---|---|---|
| full (2 MES + overlay) | 37.7% | 2.06x |
| MES only 5x | 34.0% | **2.69x** |
| MES only 6x | 38.9% | **2.97x** |

The overlay edge over plain 2 MES is **+5.7pp median** and it wins 60% of
windows — but its 5th-percentile edge is **−28.6pp**. It is a positive-median,
fat-left-tail trade, and the extra risk it adds buys less return than simply
sizing up the equity leg would.

---

## Bottom line

The steepener overlay is doing something real: it is an **equity-crisis hedge**
that added +21pp on average across six recessions and rescued the GFC. If your
objective is *not losing money when the Fed is cutting*, it delivers.

But as a **return engine it is dominated**. Across 180 rolling 5-year windows,
matching the full book's risk with plain MES produces ~22pp more return. You are
paying for the hedge in both drawdown (worst 56.9% vs 39.7%) and worst-case
outcome (−25.5% vs −1.2%), and the hedge fails in the one scenario that hurts
most — a 2022-style episode where stocks and the curve sell off together
(−32.5%, the worst episode in the whole study).

So: **keep the overlay only if you specifically want recession insurance and
will accept a flattening tail to get it. If you just want growth per unit of
risk, drop the rates legs and size the MES up instead.**

## Caveats

- Delta replay onto today's levels; fixed contract counts (risk declines as
  equity grows); rates floored at 5bp.
- ZN priced off its ~6.5y CTD, so this is a 2s/6.5s steepener in substance.
- Episodes are the worst non-overlapping 12-month flattenings (≥400-day gap);
  a different lookback would pick somewhat different windows.
- No commissions, slippage, CTD switches, or margin hikes.
- Rolling windows overlap, so the distribution is not 180 independent draws.
