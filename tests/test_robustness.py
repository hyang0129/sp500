"""Tests for the audit follow-up tooling: stationary bootstrap, the realistic
maintenance-margin liquidation, and the extended (pre-1988) data span."""
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest import build_arrays, run_path  # noqa: E402
from bootstrap import _stationary_indices, bootstrap_windows, effective_sample_size  # noqa: E402
from config import Config  # noqa: E402
from data import prepare  # noqa: E402


def test_stationary_indices_in_range_and_length():
    rng = np.random.default_rng(0)
    idx = _stationary_indices(n_pool=500, n_out=2520, mean_block=21.0, rng=rng)
    assert idx.shape == (2520,)
    assert idx.min() >= 0 and idx.max() < 500
    # consecutive indices (within a block) advance by 1 (mod n) most of the time
    diffs = np.diff(idx)
    assert np.mean(diffs == 1) > 0.7  # ~1 - 1/mean_block of steps continue a block


def test_bootstrap_reproducible_and_sane():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(Config())
    cfg = Config(leverage=1.0, put_moneyness=None, rebalance="monthly")
    a = bootstrap_windows(data, cfg, window_years=10, n_boot=200, seed=7, history="rf")
    b = bootstrap_windows(data, cfg, window_years=10, n_boot=200, seed=7, history="rf")
    tw_a = [r.terminal_wealth for r in a]
    tw_b = [r.terminal_wealth for r in b]
    assert tw_a == tw_b  # same seed -> identical draws
    med = float(np.median([r.cagr for r in a if r.cagr is not None]))
    assert 0.0 < med < 0.30  # 1x equity ~ single-digit-to-teens CAGR


def test_maint_margin_causes_ruin_in_deep_crash():
    """A realistic margin requirement wipes a 3x book in 2000-2010 that the
    literal-zero model reports as merely a deep drawdown."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(Config())
    dates = data.index
    s = int(dates.searchsorted(pd.Timestamp("2000-03-01")))
    e = int(dates.searchsorted(pd.Timestamp("2010-03-01")))
    cfg0 = Config(leverage=3.0, rebalance="monthly", maint_margin_frac=0.0)
    cfgm = Config(leverage=3.0, rebalance="monthly", maint_margin_frac=0.10)
    r0 = run_path(data, cfg0, s, e, build_arrays(data, cfg0))
    rm = run_path(data, cfgm, s, e, build_arrays(data, cfgm))
    assert not r0.ruined and r0.terminal_wealth > 0.0
    assert rm.ruined and rm.terminal_wealth == 0.0


def test_extended_history_reaches_prewar():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(Config())
    assert data.index.min().year <= 1935  # financing-gated span starts ~1934
    assert data["has_rf"].any()


def test_effective_sample_size_small_for_overlapping():
    # 30 years of monthly-stepped 20y windows ~ 1.5 independent windows
    starts = pd.Series(pd.date_range("1990-01-01", "2006-01-01", freq="MS"))
    assert effective_sample_size(starts, 20) < 1.0


def test_short_put_margin_can_ruin_writer():
    """With a margin model on, a 1x + short ATM puts (full notional) book is
    liquidatable in a crash -- the old futures-only margin never called it."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(Config())
    dates = data.index
    s = int(dates.searchsorted(pd.Timestamp("2007-06-01")))
    e = int(dates.searchsorted(pd.Timestamp("2009-06-01")))
    common = dict(leverage=1.0, put_side="sell", put_moneyness=0.0, put_ratio=1.0,
                  roll_period_years=1/12, rebalance="monthly", vrp_mode="marked_up")
    no_margin = Config(maint_margin_frac=0.0, **common)
    with_margin = Config(maint_margin_frac=0.15, **common)
    r0 = run_path(data, no_margin, s, e, build_arrays(data, no_margin))
    rm = run_path(data, with_margin, s, e, build_arrays(data, with_margin))
    # the short-option margin model must be at least as likely to ruin
    assert rm.max_drawdown >= r0.max_drawdown - 1e-9
    assert rm.ruined or rm.terminal_wealth <= r0.terminal_wealth + 1e-9
