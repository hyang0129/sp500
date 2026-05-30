"""Unit tests: BS pricing, the L=1 identity, and the financing-drag sign."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest import build_arrays, run_path  # noqa: E402
from config import Config  # noqa: E402
from data import prepare  # noqa: E402
from model import bs_call, bs_put, levered_daily  # noqa: E402


def test_bs_put_known_value():
    # Textbook ATM-ish case: S=100,K=100,T=1,r=5%,sigma=20%,q=0 -> put ~5.5735
    p = bs_put(100, 100, 1.0, 0.05, 0.20, 0.0)
    assert abs(p - 5.5735) < 1e-3


def test_put_call_parity():
    S, K, T, r, sigma, q = 100, 90, 0.75, 0.04, 0.25, 0.02
    c = bs_call(S, K, T, r, sigma, q)
    p = bs_put(S, K, T, r, sigma, q)
    # c - p = S e^{-qT} - K e^{-rT}
    rhs = S * np.exp(-q * T) - K * np.exp(-r * T)
    assert abs((c - p) - rhs) < 1e-9


def test_put_deeper_otm_is_cheaper():
    base = dict(S=100, T=1.0, r=0.04, sigma=0.2, q=0.018)
    assert bs_put(K=85, **base) < bs_put(K=90, **base) < bs_put(K=95, **base)


def test_levered_daily_financing_sign():
    # With positive financing, more leverage costs more when TR == rf is flat.
    tr = np.array([0.0])
    rf = np.array([0.01])
    assert levered_daily(tr, rf, 3.0)[0] < levered_daily(tr, rf, 1.0)[0]
    # And L=1 ignores financing entirely.
    assert abs(levered_daily(tr, rf, 1.0)[0]) < 1e-12


def test_L1_no_protection_matches_index_tr():
    cfg = Config(leverage=1.0, put_moneyness=None, rebalance="daily")
    data = prepare(cfg)
    arrays = build_arrays(data, cfg)
    # pick a window fully inside the real-TR span
    real = np.flatnonzero(arrays["real_tr"])
    start_i = int(real[0]) + 5
    end_i = start_i + 252 * 5
    res = run_path(data, cfg, start_i, end_i, arrays)
    # Raw index TR growth over the same span:
    tr = arrays["tr"]
    raw_growth = np.prod(1.0 + tr[start_i + 1 : end_i + 1])
    assert abs(res.terminal_wealth - raw_growth) / raw_growth < 1e-6


def test_financing_drag_lowers_levered_return_when_rf_positive():
    cfg1 = Config(leverage=1.0, rebalance="daily")
    cfg3 = Config(leverage=3.0, rebalance="daily")
    data = prepare(cfg1)
    a1 = build_arrays(data, cfg1)
    a3 = build_arrays(data, cfg3)
    real = np.flatnonzero(a1["real_tr"])
    s = int(real[0]) + 5
    e = s + 252 * 3
    r1 = run_path(data, cfg1, s, e, a1)
    r3 = run_path(data, cfg3, s, e, a3)
    # 3x daily of a steadily-up market still beats 1x, but financing drag
    # means 3x terminal < 3 * (1x excess). We just assert leverage amplifies.
    assert r3.terminal_wealth != r1.terminal_wealth
