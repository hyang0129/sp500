# Volcker-era stress test: $80k futures account

**Portfolio:** long 1 (or 2) MES + long 2 ZT + short 1 ZN, held as fixed
contract counts on an $80,000 account, replayed through the daily deltas of the
1979-08 → 1989-08 Volcker inflation cycle.

## What this portfolio actually is

| | |
|---|---|
| MES notional | $38,372 (1 MES) / $76,744 (2 MES) = **0.48x / 0.96x** the account |
| ZT DV01 | +$38.01/bp × 2 = **+$76.02/bp** |
| ZN DV01 | −$55.80/bp × 1 short = **−$55.80/bp** |
| Net DV01 | **+$20.22/bp** (small net long duration) |
| Margin used | ~$7,200 (1 MES) / $9,600 (2 MES) = **9–12% of the account** |

The rates legs are a **2s/10s steepener**: they lose when the curve *flattens or
inverts* (2y selling off harder than the ZN's 6.5y CTD) and win when it
*steepens*. Equity exposure is well under 1x. **This is a lightly-levered book.**

## Outcome

| mode | MES | final equity | multiple | CAGR | max DD | trough | margin call |
|---|---|---|---|---|---|---|---|
| delta | 1 | $267,359 | 3.34x | 12.8% | 24.2% | $61,713 | none |
| delta | 2 | $374,249 | 4.68x | 16.7% | 30.8% | $59,080 | none |
| level | 1 | $308,741 | 3.86x | 14.5% | 24.6% | $61,408 | none |
| level | 2 | $385,071 | 4.81x | 17.0% | 31.5% | $57,331 | none |

**It survives comfortably and compounds well.** No margin call, no ruin, worst
drawdown 24–31%. Cash-only would have returned $111,755 (delta mode), so the
positions added real value.

*delta mode* = today's levels + historical daily changes (what was asked).
*level mode* = replay actual historical yield levels, so collateral earns the
real 8–16% Volcker cash rates. Both are shown because the cash-yield assumption
is the single biggest swing factor: cash interest contributes $39.6k in delta
mode vs **$135.6k** in level mode.

## Where the money came from (delta, 1 MES)

| leg | P&L | note |
|---|---|---|
| MES | **+$101,091** | the 1982–87 bull market; the dominant driver |
| ZT (long 2) | +$84,263 | huge gains in the disinflation rally |
| ZN (short 1) | −$37,562 | the hedge leg, loses as yields fall |
| cash | +$39,567 | collateral interest |
| **net rates (ZT+ZN)** | **+$46,701** | the steepener paid, but less than equity |

## The dangerous phase: 1979–1982, not the whole decade

Each segment below is its own replay restarting at $80k, so these are regime
*signatures*, not additive:

| period | regime | ZT | ZN | net |
|---|---|---|---|---|
| 1979-08 → 1980-03 | **bear flattening (Volcker shock)** | −$39,137 | +$20,559 | **−$18,287** |
| 1980-03 → 1980-06 | Apr-1980 rate collapse | +$31,893 | −$21,004 | +$17,744 |
| 1980-06 → 1981-09 | 2nd tightening, peak rates | −$53,721 | +$31,859 | **−$15,408** |
| 1981-09 → 1986-08 | disinflation, big steepening | +$31,366 | −$30,801 | +$58,557 |
| 1986-08 → 1989-08 | late-80s re-tightening | −$4,239 | +$2,880 | +$24,906 |

The kill zone is **Aug 1979 → Mar 1980**: the replayed 2y spikes ~+740bp and the
curve inverts to **−143bp**, so the long-2s leg bleeds far more than the short-ZN
leg gains. Equity bottoms at $61,713 (−22.9%) on 1980-03-27 — then rebounds
**+31.3% in April 1980 alone** as rates collapse. Worst months: 1980-02 −12.3%,
1979-10 −10.7% (the Oct-1979 "Saturday Night Massacre"), 1987-10 −9.3%.

October 1987 costs −14.2% (1 MES) / −21.0% (2 MES) but lands when the account is
already ~3x, so it never threatens survival.

## 2 MES vs 1 MES

Doubling equity exposure raises CAGR 12.8% → 16.7% and final equity
$267k → $374k, at the cost of drawdown 24.2% → 30.8%. In this particular path
it is clearly worth it — because the replayed decade contains the 1982–87 bull
market. That is a *sample-specific* verdict, not a general one.

## What would actually break it

Scaling every leg by k (k MES / 2k ZT / −k ZN), delta mode:

| k | max DD | margin call |
|---|---|---|
| 1 | 24.2% | none |
| 2 | 51.5% | none |
| **3** | **74.6%** | **1980-03-17** |
| 4+ | — | progressively earlier (Oct 1979) |

**k = 3 is the cliff.** At 3x the stated size the account is margin-called at the
March-1980 spike — and being stopped out there means missing the entire
1982–89 recovery that makes the strategy work. Beyond k=3 the account trips the
margin wire *earlier*, which mechanically preserves more capital (it stops
trading sooner) — so the k≥4 rows are "stopped out early", not "safer".

## Caveats

1. **Fixed contract counts.** As equity grows $80k → $267k the position becomes
   proportionally smaller, so risk *declines* over the decade. A constant-risk
   book (scaling contracts with equity) would stay at the initial risk level
   throughout and would look materially worse.
2. **Delta mode floors rates at 5bp.** The replayed T-bill path hits that floor
   in 1986–87 (today's 3.71% minus a −370bp historical delta), which removes the
   cash yield in those years. Level mode avoids this.
3. **ZN is priced off a 6.5y CTD**, not the 10y point — that is the realistic
   deliverable, but it makes the position a 2s/6.5s steepener in substance.
   The 2s10s spread is reported for context.
4. **Quarterly roll at par**, no basis/CTD-switch modeling, no commissions or
   slippage, no margin-hike modeling (CME raised margins sharply in 1980; a
   `--margin-mult` flag exists to test that — at 3x margins k=2 also breaks).
5. **Equity dividends assumed 4.5%/yr**, appropriate for that era (today's S&P
   yields ~1.2%); the S&P path uses historical price returns applied to today's
   index level.
6. **Margin figures are assumptions** (MES $2,400, ZT $1,300, ZN $2,200), not
   live CME values.

## Bottom line

At the stated size this portfolio is **not** stressed to failure by the Volcker
era — it ends 3.3–4.8x higher with a 24–31% drawdown. It has a genuinely bad
18 months (Aug 1979 → early 1982) driven by curve *inversion*, and it survives
that only because it is small: 9–12% margin utilization and sub-1x equity
exposure. Triple the size and the same path produces a margin call at the March
1980 spike. The risk here is not the level of rates — it is the **flattening**,
and it arrives early.
