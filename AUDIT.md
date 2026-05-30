# Methodology Audit — Leveraged S&P 500 + Tail Protection Backtest

Audit of the analysis on branch `claude/sp500-leverage-tail-protection-jmwo3`
(README.md / SUMMARY.md and the `backtest.py` / `model.py` / `data.py` engine).
Headline numbers in `output/` were reproduced exactly; the issues below are
about whether the findings can bear the weight the write-up puts on them.

## Summary

The code is correct (financing identity, Black-Scholes pricing, leverage engine)
and the write-up is honest about several limits. The problem is inferential, not
arithmetic: the "distributions" come from a single historical path sliced into
heavily overlapping windows, and three modeling conventions all bias *toward*
the protection conclusion. The qualitative mechanics are trustworthy; the
specific percentiles and the "narrow 10-year sweet spot" are not.

## 1. "Distributions" are one path in overlapping windows (dominant issue)

Every percentile/median/P(ruin) is computed across rolling windows stepped
monthly over a single 1988–2026 history. The windows overlap massively, so they
are not independent. Effective (non-overlapping) sample sizes:

| Window | Reported n | Independent windows |
|---|---|---|
| 5y | 401 | ~6.7 |
| 10y | 341 | ~2.8 |
| 15y | 281 | ~1.6 |
| 20y | 221 | ~0.9 |

The 20y "distribution" contains **less than one** independent observation; the
10y headline has effective n≈3. Reporting a "5th percentile" of 341 windows
implies precision the data does not contain (pseudo-replication).

## 2. The 10-year tail result is one episode (n=1)

The bottom-5% windows that define the flagship tail (3x, 10y, unprotected) are
~17 adjacent monthly windows that all start near the 2000 top and end at/near
the 2009 GFC bottom (71% end Dec-2008..mid-2009; worst = Mar1999→Mar2009 at
0.085x). They are the *same episode* shifted a month at a time. So "protection
lifts 5th-pct terminal wealth ~40% at 3x/10y" is an n=1 finding. The "narrow
10-year sweet spot" follows mechanically: the U.S. sample's one lost decade
(2000–2009) is ~10y long, so it fits a 10y window and dilutes in a 20y one.

## 3. The put settles exactly at the measurement date

`_roll_indices` forces the final roll to the window end and `run_path` settles
the put's intrinsic value there, so the put always cashes out precisely when
terminal wealth is measured. That maximizes its apparent tail benefit and is a
measurement convention, not a property of the strategy.

## 4. P(ruin)≈0 is an artifact of `maintenance_frac = 0`

Ruin = literal zero equity, yet 95th-pct drawdowns are ~96–97% at 3x. A real 3x
account is margin-called (liquidated near ~25–30% equity) long before zero, so
the unprotected book's true downside is understated — exactly what protection is
meant to address.

## 5. Option pricing flatters protection's cost

- Tenor mismatch: 30-day VIX used to price a 1-year put (T=1) — underprices in
  calm regimes when puts are bought.
- No skew: 15–25% OTM puts priced off ATM VIX×1.2; index put skew is steep, so
  real premiums are higher. Both errors make protection cheaper than reality, so
  "survives realistic premiums" is optimistic.

## 6. Smaller but real

- Intra-month engine accumulates equity in the *sum* of daily levered returns
  (additive), understating compounding/decay vs a true geometric/fixed-contract
  path — part of why "monthly" looks much kinder than "daily".
- Financing at exactly the T-bill rate (no spread) flatters leverage.
- `cagr_mean` is the mean of per-window CAGRs (a geometric-rate measure), not an
  arithmetic single-period mean; the "mean falls / median rises = volatility
  drag" framing conflates window-distribution skew with single-period drag.
- One market, no bootstrap/Monte Carlo; the Japan/1929 counterfactual is named
  but never modeled, though it would likely flip the 20y sign.

## Trust / don't-trust

- Trustworthy (qualitative): leverage amplifies volatility drag; daily-reset
  LETFs decay far worse than monthly; an annual European put doesn't cushion
  intra-year; some historical 10y windows exist where 3x+put beats 3x alone.
- Not trustworthy as stated: specific percentiles, the "~40–60% tail lift," the
  "narrow 10-year sweet spot," "ruin basically never happens," "survives
  realistic premiums" — all driven by one episode, a trough-aligned put
  settlement, a 0% liquidation threshold, and understated option costs.

## Cheapest high-impact fixes

1. Report effective (non-overlapping) n beside every distributional claim.
2. Block/stationary-bootstrap daily returns; re-derive P(ruin)/p5 from those.
3. Set `maintenance_frac` to a realistic 0.25–0.30 for the headline.
4. Price OTM puts with skew/term-structure-aware vol, not ATM VIX×1.2.
5. Decouple put expiry from the measurement date.
6. Splice in price-only 1970s data and/or a Japan/1929 stress path to test the
   20y "every window recovered" conclusion.
