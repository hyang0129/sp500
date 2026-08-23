# Findings: does annually-rolled OTM put protection help leveraged S&P 500 buy-and-hold?

*Backtest over rolling 5y / 10y / 15y / 20y windows, S&P 500 total return
1988–2026 (monthly step). Headline figures use **monthly rebalancing** and
**marked-up premiums** (BS implied vol ×1.2, the realistic-cost case).
Financing = 13-week T-bill. Liquidation = `daily_path`.*

## The short answer

**Yes — but only at high leverage and shorter horizons.** Systematically buying
OTM puts raises the *geometric* (median) and *tail* (5th-percentile) outcomes
while lowering the *arithmetic* mean — exactly the volatility-drag mechanism the
hypothesis predicts — and this only pays off at **3x (marginally 2x) over ~10
year horizons**. At **1x it is pure drag**, and over **20-year horizons** the
in-sample market always recovered, so 20 years of premium cost makes the
unprotected book win the tail.

## Horizon is the dominant variable — a narrow ~10-year sweet spot

Holding leverage and strike fixed (3x, 20% OTM put, marked-up premiums) and only
varying the horizon shows the benefit is *not* monotonic in time — it appears at
~10 years and vanishes on either side:

| horizon | median CAGR (none → put) | 5th-pct terminal wealth (none → put) | verdict |
|---|---|---|---|
| 5 years  | 28.7% → 22.8% | 0.40× → 0.32× | protection **hurts** (everything) |
| **10 years** | 18.8% → **19.2%** | 0.30× → **0.43×** | protection **helps** (median *and* tail) |
| 15 years | 19.0% → 14.9% | 1.57× → 1.11× | protection hurts |
| 20 years | 14.8% → 13.5% | 6.37× → 3.96× | protection hurts |

Notice the *unprotected* 5th-percentile terminal wealth climbs with horizon
(0.40 → 0.30 → 1.57 → 6.37): only the ~10-year tail dips below water (0.30×).
That dip is the entire opportunity for protection. By 15–20 years the worst case
is already "you still made several times your money," so there is nothing left to
insure and the premium is pure drag.

### Why it helps at 10 years but not at 20 (the key mechanism)

A crash only damages your *final* number if the window ends before you recover
from it. Tail protection therefore isn't really insuring against crashes — it is
insuring against **being measured at a bad moment** (your hold ending near a
bottom). The evidence is stark in the worst windows:

- **Worst 10-year windows (3x), every one of them: Mar 1999 → Mar 2009** — they
  end at the exact bottom of the 2008 crash, at **0.08×** (you lost 92%). The
  window's clock runs out with zero recovery time, so the put's payoff lands
  precisely when wealth is measured and directly rescues the number.
- **Worst 20-year windows (3x): 1989 → 2009, ending at 2.95×** (still nearly
  tripled), or 2000 → 2020 at 4.5×. A crash in a 20-year hold is *never* fatal to
  the final number: it either sits in the middle with a decade of recovery after
  it (the put's mid-window payoff is wasted — you'd have recovered anyway), or it
  lands at the end but was preceded by a bull market that built a cushion.

The counterintuitive part: longer horizons contain *more* crashes, so the put
pays off *more often* — but **payoff timing, not payoff count, is what matters.**
A put that pays in year 8 of a 20-year hold is wasted money. Empirically, the
U.S. had a *lost decade* (the 2000s) but never *lost two decades* — and the put
protects lost decades. Add that 20 years bills double the premiums of 10, and the
long-horizon case collapses entirely.

## Where protection wins, and where it doesn't

**1x leverage — protection loses.** Median CAGR falls (10.7% → 9.5% at 20% OTM),
mean falls, and the 5th-percentile terminal wealth falls (1.08× → 0.99×). With
no ruin risk to insure against, the premium is dead weight. *Don't buy puts on
an unlevered index for long-horizon growth.*

**3x leverage, 10-year horizon — protection wins, decisively on the tail.**

| metric (3x, 10y, marked-up) | unprotected | 15% OTM | 20% OTM | 25% OTM |
|---|---|---|---|---|
| CAGR — arithmetic **mean** | 21.6% | 16.3% | 18.2% | 19.4% |
| CAGR — **median** | 18.8% | 16.8% | **19.2%** | **20.1%** |
| CAGR — 5th percentile | −11.2% | −7.0% | −8.0% | −9.5% |
| **5th-pct terminal wealth** | 0.30× | **0.48×** | 0.43× | 0.37× |
| 95th-pct max drawdown | 96.4% | 96.5% | 96.9% | 97.0% |

The put **cuts the arithmetic mean** (21.6%→18.2% at 20% OTM) while **raising
the median CAGR** (18.8%→19.2%) and **lifting the 5th-percentile terminal wealth
by ~40–60%** (0.30×→0.43×–0.48×). That is the whole thesis in one row: average
return is the wrong metric; the geometric/tail story flips the verdict.

- **Best for the survival tail: a tight 15% OTM strike** (5th-pct wealth 0.48×).
  It pays off in more scenarios, so it cushions the deepest windows best.
- **Best for median growth: a wide 25% OTM strike** (median CAGR 20.1%). It is
  cheap enough that it barely dents the upside while still trimming the worst
  tails, but it gives back some of the deep-tail protection.
- **20% OTM is the balanced middle:** highest-but-one median *and* strong tail.

**2x leverage, 10-year — the crossover.** Median CAGR slips (16.1%→14.8% at 20%
OTM) but the 5th-percentile terminal wealth *improves* (0.68×→0.72×, and 0.77×
at 15% OTM). Protection begins earning its keep but the case is marginal.

**20-year horizon — protection loses at every leverage in this sample.** E.g. at
3x, unprotected 5th-pct terminal wealth is 6.37× vs 3.96× for 20% OTM, and
median CAGR 14.8% vs 13.5%. The reason is structural to 1988–2026: **no 20-year
window ended in ruin or even deeply underwater** — the market always recovered —
so paying ~1–4% of notional in premium every year for 20 years compounds into a
drag that the (never-realized) deep-tail insurance can't repay. This is the most
sample-dependent conclusion in the study: a 20-year window containing a
permanent or decade-long impairment (1929–49, or Japan post-1989) would likely
reverse it.

## Mechanics worth flagging

- **Ruin (literal zero) basically never happens under monthly rebalancing** in
  this sample, because a monthly reset means you'd need a single *month* bad
  enough to wipe a 3x book (>33% in a month) — which 1988–2026 never delivered.
  The danger is real but shows up as **95th-percentile drawdowns near 97% at 3x**
  and 5th-percentile wealth far below 1×, not as P(ruin). Protection's job here
  is shrinking those drawdowns and lifting the low-wealth tail, which it does.
- **Daily rebalancing (LETF-style) is materially worse** than monthly via
  volatility decay: 3x median 10y CAGR drops from 18.8% (monthly) to 13.5%
  (daily), and 5th-pct wealth from 0.30× to 0.11×. A monthly-reset futures book
  is much kinder than a daily-reset ETF.
- **European, annually-settled puts don't cushion an intra-year crash** — the
  payoff only lands at the roll, and the protected equity tracks *below*
  unprotected between rolls (it paid the premium). The benefit is realized as a
  jump at each annual roll. See `output/equity_paths_2000.png` and
  `output/equity_paths_2008.png`.

## Bottom line for the investor

If you are running **2x–3x leverage with a ~10-year horizon and care about not
getting wiped out**, an annually-rolled **15–20% OTM put** raises your median
and your worst-case ending wealth net of realistic premiums — buy the
protection. Everywhere else in this sample, skip it:

- **1x, any horizon** — no ruin risk to insure; the premium is dead weight.
- **5-year horizon** — too little recovery runway for the put's "preserve the
  base" benefit to repay the premiums, and an annual European put is too coarse
  to reliably catch a short window's worst move; protection hurts every metric.
- **15–20-year horizon** — the market always recovered in-sample, so the worst
  case is already "you still made several times your money"; double-to-quadruple
  the premiums buy insurance that never pays where it counts.

The sweet spot is narrow because two forces pull in opposite directions:
**leverage** raises the payoff to protection (volatility drag scales with L², and
high leverage is what creates a below-water tail in the first place), while
**horizon** erodes it (longer holds give the market time to repay the drawdown
the put would have insured, *and* bill more premiums). They only both favor
protection together at roughly 2x–3x over ~10 years.

*Caveats: total-return data starts 1988 (no high-rate 1970s–80s); 20y
conclusions hinge on the in-sample fact that every 20y window recovered;
premiums are modeled at BS-impliedvol×1.2 and real index-put richness varies.*

---

# Update: protective puts in the 1.5-2x zone, and whether they buy leverage headroom

Re-run with the maintenance-margin call modelled (6.5% of notional), dead
windows kept at CAGR -100%, and the full 1976-2026 sample so October 1987 is in
scope. 10-year windows, monthly reset, marked-up premiums.

## In the 1.25-2.0x zone, protection is a pure cost

| L | protection | med CAGR | 5th-pct TW | vs unprotected |
|---|---|---|---|---|
| 1.50 | none | 15.72% | 0.98 | — |
| 1.50 | put20 | 14.00% | 0.98 | **-1.72pp med, +0.01 TW** |
| 1.75 | none | 16.79% | 0.88 | — |
| 1.75 | put20 | 14.85% | 0.91 | **-1.94pp med, +0.03 TW** |
| 2.00 | none | 17.47% | 0.78 | — |
| 2.00 | put20 | 16.08% | 0.84 | **-1.39pp med, +0.06 TW** |

You pay 0.9-3.0pp of annual compound growth to buy 1-7 cents on the dollar of
5th-percentile wealth. There is no ruin here to insure against (0% at every
strike and leverage), and 10 years is enough for the market to recover, so the
premium is close to dead weight. **Do not buy puts at 1.5-2x.**

## Can protection buy back the headroom lost to the 2.75x cliff?

Only if your broker gives the puts margin credit — and even then, not enough.

| L | protection | margin credit | med CAGR | ruin |
|---|---|---|---|---|
| 2.75 | none | — | 14.37% | 25.0% |
| 2.75 | put15 | no | 10.84% | **25.0%** |
| 2.75 | put15 | yes | 15.35% | **8.3%** |
| 3.00 | none | — | -1.17% | 48.5% |
| 3.00 | put15 | no | -3.70% | **48.5%** |
| 3.00 | put15 | yes | 13.98% | **14.6%** |

**Without margin credit the put does literally nothing for ruin** — 25.0% and
48.5%, identical to unprotected, because a European put settles only at the
annual roll and cannot cushion an intra-year crash. It just costs premium.

With margin credit (the realistic case for listed SPX puts in a portfolio-margin
account, where the option's value sits in account equity) ruin falls sharply,
48.5% -> 14.6% at 3x. Note this model credits *intrinsic* value only; real puts
also carry time value that spikes with vol in a crash, so this understates the
protection.

## But leverage-plus-insurance is still dominated by less leverage

| config | med CAGR | 5th-pct CAGR | 5th-pct TW | med DD | ruin |
|---|---|---|---|---|---|
| **1.75x, no puts** | **16.79%** | -1.27% | 0.88 | 61.2% | **0.0%** |
| 2.00x, no puts | 17.47% | -2.46% | 0.78 | 69.3% | 0.0% |
| 2.75x + put15 (credit) | 15.35% | **-100%** | 0.00 | 91.7% | 8.3% |
| 3.00x + put15 (credit) | 13.98% | **-100%** | 0.00 | 94.3% | 14.6% |

Protected 3x returns **less** than unprotected 1.75x (13.98% vs 16.79%) while
still liquidating 14.6% of windows and running a 94% median drawdown. Buying
insurance so you can carry more leverage is strictly worse than carrying less
leverage. The put only earned its keep in the original study because that study
compared protected-3x against unprotected-3x — never against simply
de-levering.

**Conclusion: 1.5-1.75x monthly, unprotected, is the sound configuration.**
15.7-16.8% median CAGR, roughly break-even 5th percentile, zero ruin, and clear
of the October 1987 margin wire with room.
