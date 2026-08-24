"""Tests for the short-put (put-writing) module."""
import os
import sys

import numpy as np
from scipy.stats import norm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import bs_put  # noqa: E402
from putwrite import PWConfig, put_margin, run_putwrite, strike_from_delta, load  # noqa: E402


def _put_delta(S, K, T, r, sigma, q):
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return -np.exp(-q * T) * norm.cdf(-d1)


def test_strike_from_delta_round_trips():
    for sigma in (0.12, 0.20, 0.35, 0.60):
        for d in (0.05, 0.10, 0.20):
            K = strike_from_delta(100, d, 1 / 12, 0.04, sigma, 0.018)
            assert abs(abs(_put_delta(100, K, 1 / 12, 0.04, sigma, 0.018)) - d) < 1e-6


def test_higher_vol_pushes_same_delta_further_otm():
    lo = strike_from_delta(100, 0.10, 1 / 12, 0.04, 0.12, 0.018)
    hi = strike_from_delta(100, 0.10, 1 / 12, 0.04, 0.35, 0.018)
    assert hi < lo


def test_higher_delta_collects_more_premium():
    prem = []
    for d in (0.05, 0.10, 0.20):
        K = strike_from_delta(100, d, 1 / 12, 0.04, 0.20, 0.018)
        prem.append(bs_put(100, K, 1 / 12, 0.04, 0.20, 0.018))
    assert prem[0] < prem[1] < prem[2]


def test_two_month_premium_exceeds_one_month_at_same_delta():
    k1 = strike_from_delta(100, 0.10, 1 / 12, 0.04, 0.20, 0.018)
    k2 = strike_from_delta(100, 0.10, 2 / 12, 0.04, 0.20, 0.018)
    assert bs_put(100, k2, 2 / 12, 0.04, 0.20, 0.018) > bs_put(100, k1, 1 / 12, 0.04, 0.20, 0.018)


def test_margin_is_positive_and_grows_as_strike_approaches_spot():
    m_far = put_margin(100, 90, 1.0, 0.3)
    m_near = put_margin(100, 98, 1.0, 0.9)
    assert 0 < m_far < m_near


def test_zero_weight_reproduces_cash_only():
    """w=0 must be exactly the collateral earning the bill rate."""
    d = load()
    a = run_putwrite(d, PWConfig(weight=0.0, core_leverage=0.0))
    b = run_putwrite(d, PWConfig(weight=0.0, delta=0.20, structure="roll", core_leverage=0.0))
    assert abs(a.final - b.final) < 1e-12
    assert a.n_expiries == 0
    # Not exactly zero: ^IRX printed slightly negative in 2015 and 2020, so
    # cash collateral really did tick down a hair.
    assert a.max_drawdown < 1e-3


def test_selling_puts_adds_return_over_cash():
    d = load()
    cash = run_putwrite(d, PWConfig(weight=0.0))
    sold = run_putwrite(d, PWConfig(weight=1.0, delta=0.20, structure="hold"))
    assert sold.cagr > cash.cagr
    assert sold.premium_collected > sold.payouts  # the VRP is real in-sample


def test_hold_to_expiry_beats_closing_early():
    """Theta accelerates into expiry, so capturing the final month wins."""
    d = load()
    hold = run_putwrite(d, PWConfig(weight=1.0, delta=0.10, structure="hold"))
    roll = run_putwrite(d, PWConfig(weight=1.0, delta=0.10, structure="roll"))
    assert hold.cagr > roll.cagr


# --- volatility smile ------------------------------------------------------
def test_smile_slope_sign_and_magnitude():
    from putwrite import smile_slope
    # SKEW = 100 means lognormal: no skew
    assert abs(smile_slope(100.0, 1 / 12)) < 1e-12
    # higher SKEW = steeper, and always a positive slope (IV rises as K falls)
    assert 0 < smile_slope(110.0, 1 / 12) < smile_slope(140.0, 1 / 12)


def test_iv_rises_as_strike_falls():
    from putwrite import iv_at_strike, smile_slope
    sl = smile_slope(119.8, 1 / 12)
    assert iv_at_strike(100, 90, 0.15, sl) > iv_at_strike(100, 95, 0.15, sl) > 0.15
    # upside strikes are not marked up by this downside-only smile
    assert iv_at_strike(100, 105, 0.15, sl) == 0.15


def test_strike_from_delta_smile_is_further_otm_than_flat():
    """A steeper smile means the same delta sits at a lower strike."""
    from putwrite import smile_slope, strike_from_delta, strike_from_delta_smile
    flat = strike_from_delta(100, 0.10, 1 / 12, 0.04, 0.15, 0.018)
    K, iv = strike_from_delta_smile(100, 0.10, 1 / 12, 0.04, 0.15,
                                    smile_slope(119.8, 1 / 12), 0.018)
    assert K < flat and iv > 0.15


def test_skew_model_pays_more_for_far_otm_than_flat_vix():
    """The whole point: flat-VIX underprices the tail a seller is paid for."""
    d = load()
    flat = run_putwrite(d, PWConfig(weight=1.0, delta=0.05, structure="hold"))
    skew = run_putwrite(d, PWConfig(weight=1.0, delta=0.05, structure="hold",
                                    vol_model="skew", atm_offset=0.03))
    assert skew.premium_collected > flat.premium_collected


# --- weekly vs monthly cycles ----------------------------------------------
def test_weekly_cycle_writes_about_52_a_year():
    d = load()
    m = run_putwrite(d, PWConfig(weight=1.0, delta=0.10, cycle="month"))
    w = run_putwrite(d, PWConfig(weight=1.0, delta=0.10, cycle="week"))
    yrs = 36.6
    assert 11 < m.n_expiries / yrs < 13
    assert 50 < w.n_expiries / yrs < 54


def test_same_delta_weekly_strike_is_closer_to_spot():
    from putwrite import strike_from_delta
    kw = strike_from_delta(100, 0.10, 7 / 365.25, 0.04, 0.18, 0.018)
    km = strike_from_delta(100, 0.10, 1 / 12, 0.04, 0.18, 0.018)
    assert kw > km  # weekly sits nearer the money


def test_smile_uplift_is_tenor_invariant_at_equal_delta():
    """slope ~ 1/sqrt(T) and |log-moneyness| ~ sqrt(T), so the two cancel.

    Guards against the weekly result being an artifact of the smile model.
    """
    from putwrite import smile_slope, strike_from_delta_smile
    ups = []
    for T in (1 / 12, 7 / 365.25):
        _, iv = strike_from_delta_smile(100, 0.10, T, 0.04, 0.15,
                                        smile_slope(119.8, T), 0.018)
        ups.append(iv - 0.15)
    assert abs(ups[0] - ups[1]) < 0.01  # within 1 vol point


def test_transaction_costs_reduce_returns_and_bite_harder_weekly():
    d = load()
    def cagr(cyc, cf):
        return run_putwrite(d, PWConfig(weight=1.0, delta=0.20, cycle=cyc,
                                        vol_model="skew", atm_offset=0.03,
                                        cost_frac=cf)).cagr
    m0, m2 = cagr("month", 0.0), cagr("month", 0.25)
    w0, w2 = cagr("week", 0.0), cagr("week", 0.25)
    assert m2 < m0 and w2 < w0
    assert (w0 - w2) > (m0 - m2)  # 52 rolls/yr pays more toll than 12


# --- weekly roll schedule / weekend exposure -------------------------------
def test_weekly_spans_all_write_about_52_a_year():
    d = load()
    for span in ("mon_mon", "fri_fri", "mon_fri"):
        r = run_putwrite(d, PWConfig(weight=1.0, delta=0.10, cycle="week",
                                     weekly_span=span))
        assert 50 < r.n_expiries / 36.6 < 54


def test_mon_fri_collects_less_premium_by_sqrt_time():
    """4 calendar days vs 7: premium must scale as sqrt(4/7) per option."""
    from model import bs_put
    from putwrite import strike_from_delta
    prem = []
    for T in (7 / 365.25, 4 / 365.25):
        K = strike_from_delta(100, 0.10, T, 0.04, 0.18, 0.018)
        prem.append(bs_put(100, K, T, 0.04, 0.18, 0.018))
    assert abs(prem[1] / prem[0] - np.sqrt(4 / 7)) < 0.02


def test_weekend_flat_schedule_survives_1987_better():
    """Black Monday was a weekend gap; not holding over it must help."""
    d = load()
    def final(span):
        return run_putwrite(d, PWConfig(weight=1.0, delta=0.20, cycle="week",
                                        weekly_span=span, vol_model="skew",
                                        atm_offset=0.0, start="1987-06-01",
                                        end="1987-12-31")).final
    assert final("mon_fri") > final("fri_fri") > final("mon_mon")


def test_no_week_is_ever_skipped_by_the_roll_calendar():
    """Regression: a Friday holiday must not skip the week.

    Skipping would leave the previous week's option open for a fortnight while
    still priced as a one-week option.
    """
    d = load()
    for span in ("mon_mon", "tue_tue", "wed_wed", "thu_thu", "fri_fri", "mon_fri"):
        r = run_putwrite(d, PWConfig(weight=1.0, delta=0.10, cycle="week",
                                     weekly_span=span))
        assert 51.5 < r.n_expiries / 36.6 < 52.7, f"{span}: {r.n_expiries}"


def test_roll_day_choice_is_second_order():
    """Any 7-day weekly roll day should land within ~2pp of the others."""
    d = load()
    cagrs = []
    for span in ("mon_mon", "tue_tue", "wed_wed", "thu_thu", "fri_fri"):
        cagrs.append(run_putwrite(d, PWConfig(weight=1.0, delta=0.20, cycle="week",
                                              weekly_span=span, vol_model="skew",
                                              atm_offset=0.03)).cagr)
    assert max(cagrs) - min(cagrs) < 0.02
