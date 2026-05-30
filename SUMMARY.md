# Findings: does annually-rolled OTM put protection help leveraged S&P 500 buy-and-hold?

*Backtest over rolling 10y and 20y windows, S&P 500 total return 1988–2026
(341 ten-year windows, 221 twenty-year windows, monthly step). Headline figures
use **monthly rebalancing** and **marked-up premiums** (BS implied vol ×1.2, the
realistic-cost case). Financing = 13-week T-bill. Liquidation = `daily_path`.*

## The short answer

**Yes — but only at high leverage and shorter horizons.** Systematically buying
OTM puts raises the *geometric* (median) and *tail* (5th-percentile) outcomes
while lowering the *arithmetic* mean — exactly the volatility-drag mechanism the
hypothesis predicts — and this only pays off at **3x (marginally 2x) over ~10
year horizons**. At **1x it is pure drag**, and over **20-year horizons** the
in-sample market always recovered, so 20 years of premium cost makes the
unprotected book win the tail.

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
protection. If you are at **1x**, or genuinely have a **20-year+ horizon and the
stomach to ride drawdowns to recovery**, the premium is a net drag in this
sample — skip it. The crossover is driven by leverage (volatility drag scales
with L²) and by horizon (longer horizons give the market time to repay the
drawdown the put would have insured).

*Caveats: total-return data starts 1988 (no high-rate 1970s–80s); 20y
conclusions hinge on the in-sample fact that every 20y window recovered;
premiums are modeled at BS-impliedvol×1.2 and real index-put richness varies.*
