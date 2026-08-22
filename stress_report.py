"""Charts and tables for the Volcker-era futures stress test.

Writes to output/:
    volcker_equity_curves.png   equity paths + the replayed rate path
    volcker_attribution.png     P&L attribution by leg
    volcker_breaking_point.png  drawdown / survival vs position size
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from stress_test import (  # noqa: E402
    StressConfig, current_levels, load_panel, run_stress,
)

OUT = "output"


def replayed_rates(cfg: StressConfig) -> pd.DataFrame:
    win, cur = load_panel(cfg), current_levels(cfg)
    d0 = win.iloc[0]
    if cfg.mode == "delta":
        df = pd.DataFrame({
            "2y": cur["y2"] * 100 + (win["y2"] - d0["y2"]) * 100,
            "10y": cur["y10"] * 100 + (win["y10"] - d0["y10"]) * 100,
            "T-bill": cur["bill"] * 100 + (win["bill"] - d0["bill"]) * 100,
        }, index=win.index).clip(lower=cfg.rate_floor * 100)
    else:
        df = pd.DataFrame({"2y": win["y2"] * 100, "10y": win["y10"] * 100,
                           "T-bill": win["bill"] * 100}, index=win.index)
    df["2s10s"] = df["10y"] - df["2y"]
    return df


def chart_equity_curves(path=f"{OUT}/volcker_equity_curves.png"):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    styles = {1.0: dict(color="steelblue", lw=1.8), 2.0: dict(color="firebrick", lw=1.8)}
    for nm in (1.0, 2.0):
        for mode, ls in (("delta", "-"), ("level", "--")):
            r = run_stress(StressConfig(n_mes=nm, mode=mode))
            ax1.plot(r.curve.index, r.curve.values, ls=ls,
                     label=f"{nm:g} MES [{mode}] -> ${r.final_equity:,.0f}", **styles[nm])
    # cash-only baseline (delta mode)
    cfg = StressConfig(n_mes=0, n_zt=0, n_zn=0, mode="delta")
    rc = run_stress(cfg)
    ax1.plot(rc.curve.index, rc.curve.values, color="grey", lw=1.2, ls=":",
             label=f"cash only -> ${rc.final_equity:,.0f}")
    ax1.axhline(80_000, color="black", lw=0.8)
    ax1.set_yscale("log")
    ax1.set_ylabel("account equity ($, log)")
    ax1.set_title("$80k futures account through the Volcker cycle\n"
                  "long 1-2 MES + long 2 ZT + short 1 ZN (fixed contracts)")
    ax1.legend(fontsize=8, loc="upper left")
    ax1.grid(alpha=0.3)

    rr = replayed_rates(StressConfig())
    ax2.plot(rr.index, rr["2y"], color="darkorange", lw=1.2, label="2y (ZT)")
    ax2.plot(rr.index, rr["10y"], color="purple", lw=1.2, label="10y")
    ax2.fill_between(rr.index, rr["2s10s"], 0,
                     where=rr["2s10s"] < 0, color="red", alpha=0.25, label="curve INVERTED")
    ax2.fill_between(rr.index, rr["2s10s"], 0,
                     where=rr["2s10s"] >= 0, color="green", alpha=0.18, label="curve steep")
    ax2.axhline(0, color="black", lw=0.8)
    ax2.set_ylabel("yield / spread (%)")
    ax2.set_xlabel("replayed date (Volcker-era deltas applied to today's levels)")
    ax2.legend(fontsize=8, ncol=4)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def chart_attribution(path=f"{OUT}/volcker_attribution.png"):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, mode in zip(axes, ("delta", "level")):
        labels, vals = [], []
        for nm in (1.0, 2.0):
            r = run_stress(StressConfig(n_mes=nm, mode=mode))
            for k in ("cash", "MES", "ZT", "ZN"):
                labels.append(f"{k}\n{nm:g}MES")
                vals.append(r.attrib[k])
        colors = ["grey", "steelblue", "seagreen", "firebrick"] * 2
        ax.bar(range(len(vals)), vals, color=colors)
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels(labels, fontsize=7)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title(f"{mode} mode")
        ax.grid(alpha=0.3, axis="y")
    axes[0].set_ylabel("cumulative P&L ($)")
    fig.suptitle("Where the money came from — 10y Volcker replay on an $80k account")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def chart_breaking_point(path=f"{OUT}/volcker_breaking_point.png"):
    ks = [1, 2, 3, 4, 5, 6, 8, 10]
    dd, fin, breach = [], [], []
    for k in ks:
        r = run_stress(StressConfig(n_mes=1.0 * k, n_zt=2.0 * k, n_zn=-1.0 * k, mode="delta"))
        dd.append(r.max_drawdown * 100)
        fin.append(r.final_equity)
        breach.append(r.margin_breach is not None)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    cols = ["firebrick" if b else "seagreen" for b in breach]
    ax1.bar([str(k) for k in ks], dd, color=cols)
    ax1.axhline(100, color="black", lw=0.8)
    ax1.set_xlabel("size multiple k  (k MES / 2k ZT / -k ZN)")
    ax1.set_ylabel("max drawdown (%)")
    ax1.set_title("Drawdown vs size (red = margin call)")
    ax2.bar([str(k) for k in ks], fin, color=cols)
    ax2.axhline(80_000, color="black", lw=0.8, ls="--", label="starting $80k")
    ax2.set_xlabel("size multiple k")
    ax2.set_ylabel("final equity ($)")
    ax2.set_title("Final equity vs size")
    ax2.legend()
    for a in (ax1, ax2):
        a.grid(alpha=0.3, axis="y")
    fig.suptitle("How much size breaks the account (Volcker deltas, 1979-1989)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    chart_equity_curves()
    chart_attribution()
    chart_breaking_point()
    print(f"Wrote charts to {OUT}/volcker_*.png")


if __name__ == "__main__":
    main()
