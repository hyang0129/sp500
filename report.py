"""Metrics tables (§5) and charts (§7) from the experiment results.

Reads output/results.csv (produced by experiments.py) and writes:
    output/summary_<window>y.csv  -- per-cell metric tables
    output/cagr_box_<window>y.png
    output/p_ruin.png
    output/p5_terminal_<window>y.png
    output/equity_paths_2008.png, output/equity_paths_2000.png
and prints the headline tables to stdout.
"""
from __future__ import annotations

import os
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from backtest import build_arrays, run_path  # noqa: E402
from config import Config  # noqa: E402
from data import prepare  # noqa: E402

PROT_ORDER = ["none", "put15", "put20", "put25"]
PROT_LABEL = {"none": "no put", "put15": "15% OTM", "put20": "20% OTM", "put25": "25% OTM"}


def _pct(s, q):
    return np.percentile(s, q) if len(s) else np.nan


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Per-cell metrics across the rolling-window distribution (§5)."""
    rows = []
    keys = ["window_years", "leverage", "protection", "rebalance", "vrp_mode"]
    for key, g in df.groupby(keys):
        cg = g.loc[~g["ruined"], "cagr"].to_numpy()
        tw = g["terminal_wealth"].to_numpy()
        logw = g["log_terminal"].replace(-np.inf, np.nan).dropna().to_numpy()
        # arithmetic mean of per-window simple terminal returns (annualized-ish
        # proxy: mean of window CAGRs) vs geometric/median story.
        rows.append(
            dict(
                window_years=key[0], leverage=key[1], protection=key[2],
                rebalance=key[3], vrp_mode=key[4], n=len(g),
                cagr_median=_pct(cg, 50), cagr_p5=_pct(cg, 5), cagr_p25=_pct(cg, 25),
                cagr_p75=_pct(cg, 75), cagr_p95=_pct(cg, 95),
                cagr_mean=np.mean(cg) if len(cg) else np.nan,
                mdd_median=_pct(g["max_drawdown"], 50),
                mdd_p95=_pct(g["max_drawdown"], 95),
                p_ruin=g["ruined"].mean(),
                tw_p5=_pct(tw, 5), tw_median=_pct(tw, 50),
                median_logwealth=np.median(logw) if len(logw) else np.nan,
            )
        )
    out = pd.DataFrame(rows)
    out["_p"] = out["protection"].map({p: i for i, p in enumerate(PROT_ORDER)})
    out = out.sort_values(["window_years", "rebalance", "vrp_mode", "leverage", "_p"]).drop(columns="_p")
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def chart_cagr_box(df, window_years, rebalance, vrp_mode, path):
    sub = df[(df.window_years == window_years) & (df.rebalance == rebalance)
             & ((df.vrp_mode == vrp_mode) | (df.protection == "none"))]
    levs = sorted(sub.leverage.unique())
    fig, axes = plt.subplots(1, len(levs), figsize=(4 * len(levs), 5), sharey=True)
    if len(levs) == 1:
        axes = [axes]
    for ax, L in zip(axes, levs):
        data, labels = [], []
        for p in PROT_ORDER:
            cell = sub[(sub.leverage == L) & (sub.protection == p)]
            cg = cell.loc[~cell.ruined, "cagr"].to_numpy()
            if len(cg):
                data.append(cg * 100)
                labels.append(PROT_LABEL[p])
        bp = ax.boxplot(data, tick_labels=labels, showmeans=True, whis=(5, 95))
        ax.axhline(0, color="grey", lw=0.8, ls="--")
        ax.set_title(f"{L:g}x leverage")
        ax.set_xlabel("protection")
        ax.tick_params(axis="x", rotation=30)
    axes[0].set_ylabel("CAGR (%)")
    fig.suptitle(f"CAGR distribution — {window_years}y windows, {rebalance} rebal, {vrp_mode} premiums\n"
                 "(box = IQR, whiskers = 5–95th pctile, ▲ = mean)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def chart_p_ruin(df, rebalance, vrp_mode, path):
    sub = df[(df.rebalance == rebalance)
             & ((df.vrp_mode == vrp_mode) | (df.protection == "none"))]
    s = summarize(sub)
    wys = sorted(s.window_years.unique())
    fig, axes = plt.subplots(1, len(wys), figsize=(6 * len(wys), 5), sharey=True)
    if len(wys) == 1:
        axes = [axes]
    for ax, wy in zip(axes, wys):
        ss = s[s.window_years == wy]
        levs = sorted(ss.leverage.unique())
        x = np.arange(len(levs))
        w = 0.2
        for i, p in enumerate(PROT_ORDER):
            vals = [ss[(ss.leverage == L) & (ss.protection == p)]["p_ruin"].mean() for L in levs]
            ax.bar(x + (i - 1.5) * w, np.array(vals) * 100, w, label=PROT_LABEL[p])
        ax.set_xticks(x)
        ax.set_xticklabels([f"{L:g}x" for L in levs])
        ax.set_title(f"{wy}y windows")
        ax.set_xlabel("leverage")
    axes[0].set_ylabel("P(ruin) (%)")
    axes[0].legend()
    fig.suptitle(f"Probability of ruin — {rebalance} rebal, {vrp_mode} premiums")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def chart_p5_terminal(df, window_years, rebalance, vrp_mode, path):
    sub = df[(df.window_years == window_years) & (df.rebalance == rebalance)
             & ((df.vrp_mode == vrp_mode) | (df.protection == "none"))]
    s = summarize(sub)
    levs = sorted(s.leverage.unique())
    x = np.arange(len(levs))
    w = 0.2
    fig, ax = plt.subplots(figsize=(8, 5))
    for i, p in enumerate(PROT_ORDER):
        vals = [s[(s.leverage == L) & (s.protection == p)]["tw_p5"].mean() for L in levs]
        ax.bar(x + (i - 1.5) * w, vals, w, label=PROT_LABEL[p])
    ax.axhline(1.0, color="grey", lw=0.8, ls="--", label="break-even (1x money)")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{L:g}x" for L in levs])
    ax.set_ylabel("5th-percentile terminal wealth (×)")
    ax.set_xlabel("leverage")
    ax.set_title(f"5th-pctile terminal wealth — {window_years}y, {rebalance}, {vrp_mode} premiums\n"
                 "(the 'did I survive' tail)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def chart_equity_paths(data, start_date, label, path, leverage=3.0, moneyness=0.20):
    """Protected vs unprotected equity curves for a window starting near a crash."""
    dates = data.index
    start_i = int(dates.searchsorted(pd.Timestamp(start_date)))
    end_i = int(dates.searchsorted(dates[start_i] + pd.DateOffset(years=10)))
    end_i = min(end_i, len(dates) - 1)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for m, style in [(None, dict(color="firebrick", label=f"{leverage:g}x unprotected")),
                     (moneyness, dict(color="seagreen", label=f"{leverage:g}x + {int(moneyness*100)}% OTM put"))]:
        cfg = Config(leverage=leverage, put_moneyness=m, rebalance="monthly", vrp_mode="marked_up")
        arrays = build_arrays(data, cfg)
        res = run_path(data, cfg, start_i, end_i, arrays, record_curve=True)
        if res.curve is not None:
            ax.plot(res.curve.index, res.curve.values, lw=1.6, **style)
    # 1x index TR reference
    cfg1 = Config(leverage=1.0, put_moneyness=None, rebalance="monthly")
    a1 = build_arrays(data, cfg1)
    r1 = run_path(data, cfg1, start_i, end_i, a1, record_curve=True)
    if r1.curve is not None:
        ax.plot(r1.curve.index, r1.curve.values, lw=1.2, color="steelblue", ls="--", label="1x index (TR)")
    ax.set_yscale("log")
    ax.set_ylabel("equity (×, log scale)")
    ax.set_title(f"Equity paths through {label} — 10y window from {dates[start_i].date()}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
def headline_table(s: pd.DataFrame, window_years: int, rebalance="monthly", vrp_mode="marked_up") -> str:
    cols = ["leverage", "protection", "cagr_median", "cagr_mean", "cagr_p5",
            "mdd_median", "mdd_p95", "p_ruin", "tw_p5", "tw_median"]
    ss = s[(s.window_years == window_years) & (s.rebalance == rebalance)
           & ((s.vrp_mode == vrp_mode) | (s.protection == "none"))][cols].copy()
    for c in ["cagr_median", "cagr_mean", "cagr_p5", "mdd_median", "mdd_p95", "p_ruin"]:
        ss[c] = (ss[c] * 100).round(1)
    ss[["tw_p5", "tw_median"]] = ss[["tw_p5", "tw_median"]].round(2)
    ss = ss.rename(columns={
        "cagr_median": "CAGR_med%", "cagr_mean": "CAGR_mean%", "cagr_p5": "CAGR_p5%",
        "mdd_median": "MDD_med%", "mdd_p95": "MDD_p95%", "p_ruin": "Ruin%",
        "tw_p5": "TW_p5x", "tw_median": "TW_med x"})
    return ss.to_string(index=False)


def main(results_path="output/results.csv", outdir="output"):
    df = pd.read_csv(results_path, parse_dates=["start", "end"])
    s = summarize(df)
    os.makedirs(outdir, exist_ok=True)
    for wy in sorted(df.window_years.unique()):
        s[s.window_years == wy].to_csv(f"{outdir}/summary_{wy}y.csv", index=False)
        print(f"\n===== {wy}y windows | monthly rebalance | marked-up premiums =====")
        print(headline_table(s, wy))

    # Charts (primary lens: monthly rebalance, marked-up = realistic premiums)
    for wy in sorted(df.window_years.unique()):
        chart_cagr_box(df, wy, "monthly", "marked_up", f"{outdir}/cagr_box_{wy}y.png")
        chart_p5_terminal(df, wy, "monthly", "marked_up", f"{outdir}/p5_terminal_{wy}y.png")
    chart_p_ruin(df, "monthly", "marked_up", f"{outdir}/p_ruin.png")
    if "daily" in df.rebalance.unique():
        chart_p_ruin(df, "daily", "marked_up", f"{outdir}/p_ruin_daily.png")
        chart_cagr_box(df, 10, "daily", "marked_up", f"{outdir}/cagr_box_10y_daily.png")

    # Representative crash windows
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = prepare(Config())
    chart_equity_paths(data, "2005-01-03", "the 2008 crisis", f"{outdir}/equity_paths_2008.png")
    chart_equity_paths(data, "2000-01-03", "the 2000–02 dot-com bust", f"{outdir}/equity_paths_2000.png")
    print(f"\nWrote summary tables and charts to {outdir}/")


if __name__ == "__main__":
    main()
