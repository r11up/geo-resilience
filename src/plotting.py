"""Low-level, reusable chart-drawing primitives. Ports notebook Sections 11,
16b (heatmap only), 12c (regime-trajectory only), 18, and 21f-21o unchanged --
every color, size, and formatting choice is preserved verbatim.

These functions take plain data (DataFrames/Series/dicts) and styling
parameters and return a Matplotlib ``Figure``; they know nothing about which
paper figure they're being used for. Paper-figure-named orchestration (which
columns, which title, where it's saved) lives in ``src/visualization.py``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from src import config
from src.utils import country_name

logger = logging.getLogger("nepal_south_asia")

plt.rcParams.update(
    {
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "font.size": 10.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": config.GRID_COLOR,
        "grid.linewidth": 0.6,
        "axes.edgecolor": "#333333",
    }
)


def _save(fig: plt.Figure, savepath: str | Path | None) -> None:
    """Saves ``fig`` as both a 300dpi PNG and a vector PDF, if ``savepath`` is given."""
    if not savepath:
        return
    savepath = Path(savepath)
    fig.savefig(savepath, bbox_inches="tight")
    fig.savefig(savepath.with_suffix(".pdf"), bbox_inches="tight")


def _big_number_formatter(x: float, pos: int | None = None) -> str:
    """Renders large USD/count axis values as e.g. '140B' / '7.2M' instead of
    raw scientific notation (1.4e11)."""
    ax = abs(x)
    if ax >= 1e9:
        return f"{x/1e9:.1f}B" if (ax / 1e9) < 10 else f"{x/1e9:.0f}B"
    if ax >= 1e6:
        return f"{x/1e6:.1f}M" if (ax / 1e6) < 10 else f"{x/1e6:.0f}M"
    if ax >= 1e3:
        return f"{x/1e3:.0f}K"
    return f"{x:.0f}"


def plot_trend_panel(
    wide_df: pd.DataFrame,
    indicators: list[tuple[str, str] | tuple[str, str, str]],
    focal_iso3: str = config.FOCAL,
    title: str | None = None,
    ncols: int = 3,
    savepath: str | Path | None = None,
) -> plt.Figure:
    """Small-multiples trend panel, one subplot per indicator, one line per country.

    ``indicators``: list of ``(code, label)`` or ``(code, label, format_hint)``
    tuples. ``format_hint="big_number"`` applies the billions/millions axis
    formatter. The focal country (Nepal) is drawn bolder and listed first in
    the legend.
    """
    n = len(indicators)
    ncols = min(ncols, n)
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.6 * ncols, 3.4 * nrows), squeeze=False)
    axes_flat = axes.flatten()
    focal_name = country_name(focal_iso3)
    for ax, item in zip(axes_flat, indicators):
        col, label = item[0], item[1]
        fmt_hint = item[2] if len(item) > 2 else None
        for iso3, grp in wide_df.groupby("iso3"):
            grp = grp.sort_values("year")
            is_focal = iso3 == focal_iso3
            ax.plot(
                grp["year"],
                grp[col],
                label=country_name(iso3),
                color=config.COUNTRY_COLORS.get(iso3, "#999999"),
                linewidth=2.4 if is_focal else 1.4,
                alpha=1.0 if is_focal else 0.85,
                zorder=5 if is_focal else 3,
            )
        ax.set_title(label, fontsize=10.5, loc="left")
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=6))
        if fmt_hint == "big_number":
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(_big_number_formatter))
    for ax in axes_flat[n:]:
        ax.axis("off")
    handles, labels_ = axes_flat[0].get_legend_handles_labels()
    by_label = dict(zip(labels_, handles))
    ordered = sorted(by_label, key=lambda name: (name != focal_name, name))
    fig.legend(
        [by_label[c] for c in ordered],
        ordered,
        loc="lower center",
        ncol=min(len(by_label), 6),
        frameon=False,
        bbox_to_anchor=(0.5, -0.03),
    )
    if title:
        fig.suptitle(title, fontsize=13, y=1.02, fontweight="bold")
    fig.tight_layout()
    _save(fig, savepath)
    return fig


def plot_correlation_heatmap(
    corr_display: pd.DataFrame,
    title: str = "Correlation heatmap",
    ylabel_note: str = "",
    savepath: str | Path | None = None,
) -> plt.Figure:
    """Annotated correlation heatmap. ``corr_display`` must already have
    human-readable row/column labels (see ``src.utils.label_for``)."""
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    im = ax.imshow(corr_display.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr_display.columns)))
    ax.set_xticklabels(corr_display.columns, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(len(corr_display.index)))
    ax.set_yticklabels(corr_display.index, fontsize=9)
    for i in range(corr_display.shape[0]):
        for j in range(corr_display.shape[1]):
            v = corr_display.values[i, j]
            ax.text(
                j, i, f"{v:.2f}", ha="center", va="center", color="white" if abs(v) > 0.55 else "black", fontsize=8.5
            )
    fig.colorbar(im, ax=ax, shrink=0.8, label=ylabel_note or "Pearson r")
    ax.set_title(title, fontsize=11.5, fontweight="bold")
    fig.tight_layout()
    _save(fig, savepath)
    return fig


def plot_regime_trajectory(
    panel: pd.DataFrame,
    regime_col: str = "v2x_regime",
    focal_iso3: str = config.FOCAL,
    title: str = "Democratic Resilience — Regimes of the World classification (V-Dem)",
    savepath: str | Path | None = None,
) -> plt.Figure | None:
    """V-Dem 'Regimes of the World' trajectory (0=Closed Autocracy .. 3=Liberal
    Democracy), one line per country -- Fig. 2's own terminal node."""
    if regime_col not in panel.columns:
        return None
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for iso3, grp in panel.groupby("iso3"):
        grp = grp.sort_values("year").dropna(subset=[regime_col])
        if grp.empty:
            continue
        is_focal = iso3 == focal_iso3
        ax.plot(
            grp["year"],
            grp[regime_col],
            label=country_name(iso3),
            color=config.COUNTRY_COLORS.get(iso3, "#999999"),
            linewidth=2.6 if is_focal else 1.5,
            alpha=1.0 if is_focal else 0.85,
            marker="o",
            markersize=3.2,
            zorder=5 if is_focal else 3,
        )
    ax.set_yticks(list(config.REGIME_CATEGORY_LABELS.keys()))
    ax.set_yticklabels(list(config.REGIME_CATEGORY_LABELS.values()), fontsize=9)
    ax.set_ylim(-0.4, 3.4)
    ax.set_ylabel("Regime category (V-Dem Regimes of the World)")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=8))
    ax.set_title(title, fontsize=12, loc="left", fontweight="bold")
    handles, labels_ = ax.get_legend_handles_labels()
    by_label = dict(zip(labels_, handles))
    ordered = sorted(by_label, key=lambda name: (name != country_name(focal_iso3), name))
    ax.legend(
        [by_label[c] for c in ordered],
        ordered,
        frameon=False,
        fontsize=8.5,
        loc="upper left",
        ncol=2,
        bbox_to_anchor=(0.0, -0.16),
    )
    fig.tight_layout()
    _save(fig, savepath)
    return fig


def plot_forecast_fan(
    history: pd.Series,
    forecasts_dict: dict[str, pd.DataFrame | pd.Series],
    ylabel: str = "",
    title: str | None = None,
    savepath: str | Path | None = None,
) -> plt.Figure:
    """Observed series + one dashed line (with shaded interval, if available)
    per forecasting model."""
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.plot(history.index, history.values, color="#222222", linewidth=1.8, label="Observed", zorder=5)
    palette = ["#B23A48", "#2A6F77", "#C98A2C"]
    for (name, fc), color in zip(forecasts_dict.items(), palette):
        if hasattr(fc, "columns") and "forecast" in fc.columns:
            ax.plot(fc.index, fc["forecast"], color=color, linewidth=2.0, linestyle="--", label=f"{name} forecast")
            ax.fill_between(fc.index, fc["lower"], fc["upper"], color=color, alpha=0.15)
        else:
            ax.plot(fc.index, fc.values, color=color, linewidth=2.0, linestyle="--", label=f"{name} forecast")
    ax.axvline(history.index.max(), color="#999999", linewidth=0.8, linestyle=":")
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=8))
    ax.legend(frameon=False, fontsize=9, loc="best")
    if title:
        ax.set_title(title, fontsize=12, loc="left", fontweight="bold")
    fig.tight_layout()
    _save(fig, savepath)
    return fig


def plot_wave_comparison(
    df: pd.DataFrame,
    value_col: str,
    ylabel: str,
    title: str,
    country_order: list[str] | None = None,
    savepath: str | Path | None = None,
) -> tuple[plt.Figure, pd.DataFrame]:
    """Grouped bar chart: one group per country, one bar per wave. A
    BEFORE/AFTER comparison, not a trend line (two waves can't forecast)."""
    agg = df.groupby(["country", "wave"])[value_col].mean().unstack()
    if country_order:
        agg = agg.reindex(country_order)
    waves = list(agg.columns)
    x = np.arange(len(agg.index))
    width = 0.8 / len(waves)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, wave in enumerate(waves):
        offset = (i - (len(waves) - 1) / 2) * width
        ax.bar(
            x + offset, agg[wave].values, width=width, color=config.WAVE_COLORS.get(str(wave), "#999999"), label=wave
        )
    ax.set_xticks(x)
    ax.set_xticklabels(agg.index, rotation=0)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12, loc="left", fontweight="bold")
    ax.legend(frameon=False, title="Wave")
    fig.tight_layout()
    _save(fig, savepath)
    return fig, agg


def plot_trust_by_institution(
    df: pd.DataFrame,
    trust_cols: list[str],
    labels: dict[str, str],
    wave_label: str,
    title_suffix: str = "",
    savepath: str | Path | None = None,
) -> tuple[plt.Figure, pd.Series]:
    """Horizontal bar chart: mean trust per institution (not the aggregate
    composite), for ONE wave, ranked high-to-low."""
    means = df[trust_cols].mean().rename(index=labels).sort_values()
    fig, ax = plt.subplots(figsize=(7, 0.4 * len(means) + 1.2))
    ax.barh(means.index, means.values, color="#5B6EE1")
    ax.set_xlabel("Mean trust (1-4 scale)")
    ax.set_title(f"Institutional trust, {wave_label}{title_suffix}", fontsize=11, loc="left", fontweight="bold")
    ax.set_xlim(1, 4)
    fig.tight_layout()
    _save(fig, savepath)
    return fig, means


def plot_mediation_result(
    params: pd.DataFrame,
    indirect: dict[str, Any],
    condition_col: str,
    outcome_col: str,
    condition_label: str | None = None,
    outcome_label: str | None = None,
    title_suffix: str = "",
    savepath: str | Path | None = None,
) -> plt.Figure:
    """Two panels: (1) a hand-drawn path diagram with the three key structural
    coefficients, and (2) the bootstrap distribution of the indirect effect a*b.

    ``condition_col``/``outcome_col`` are the real column names used to fit
    the model (needed to look up coefficients in ``params``);
    ``condition_label``/``outcome_label`` are what actually gets drawn in the
    boxes.
    """
    condition_label = condition_label or condition_col
    outcome_label = outcome_label or outcome_col

    def _coef(lval: str, rval: str) -> float | None:
        row = params[(params["lval"] == lval) & (params["rval"] == rval) & (params["op"] == "~")]
        return float(row["Estimate"].values[0]) if len(row) else None

    a = _coef("Trust", condition_col)
    b = _coef(outcome_col, "Trust")
    c = _coef(outcome_col, condition_col)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    boxes = {"condition": (1.3, 3), "Trust": (5, 5), "outcome": (8.7, 3)}
    labels = {"condition": condition_label, "Trust": "Trust\n(latent)", "outcome": outcome_label}
    for key, (x, y) in boxes.items():
        ax.add_patch(
            plt.Rectangle((x - 1.3, y - 0.6), 2.6, 1.2, fill=True, facecolor="#EDEFF1", edgecolor="#333333", zorder=2)
        )
        ax.text(x, y, labels[key], ha="center", va="center", fontsize=8.5, zorder=3)

    def arrow(p1: tuple[float, float], p2: tuple[float, float], label: str) -> None:
        ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle="->", color="#333333", lw=1.6))
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx, my + 0.28, label, ha="center", fontsize=9, color="#B23A48", fontweight="bold")

    arrow((2.3, 3.5), (4, 4.6), f"a = {a:.2f}" if a is not None else "a = ?")
    arrow((6, 4.6), (7.7, 3.5), f"b = {b:.2f}" if b is not None else "b = ?")
    arrow((2.3, 2.7), (7.7, 2.7), f"c' = {c:.2f}" if c is not None else "c' = ?")
    ax.set_title(f"Path model{title_suffix}", fontsize=11, loc="left", fontweight="bold")

    ax2 = axes[1]
    boots = np.asarray(indirect.get("boot_samples", []))
    if len(boots):
        ax2.hist(boots, bins=30, color="#5B6EE1", alpha=0.75)
        ax2.axvline(0, color="#333333", linewidth=1, linestyle="--")
        ax2.axvline(indirect["ci_2.5"], color="#B23A48", linewidth=1.2, linestyle=":")
        ax2.axvline(indirect["ci_97.5"], color="#B23A48", linewidth=1.2, linestyle=":")
        ax2.set_title(
            f"Bootstrapped indirect effect (a x b), n={indirect['n_successful_bootstraps']}",
            fontsize=11,
            loc="left",
            fontweight="bold",
        )
        ax2.set_xlabel(
            f"mean={indirect['indirect_effect_mean']:.3f}  "
            f"95% CI [{indirect['ci_2.5']:.3f}, {indirect['ci_97.5']:.3f}]  "
            f"significant={indirect['significant']}",
            fontsize=8.5,
        )
    else:
        ax2.text(0.5, 0.5, "No bootstrap samples to plot", ha="center", va="center")
        ax2.axis("off")
    fig.tight_layout()
    _save(fig, savepath)
    return fig


def plot_abs_vs_expert_governance(
    abs_df: pd.DataFrame,
    panel_df: pd.DataFrame,
    expert_col: str,
    expert_label: str,
    wave_year_map: dict[str, int] | None = None,
    savepath: str | Path | None = None,
) -> tuple[plt.Figure | None, pd.DataFrame]:
    """Scatter: expert-coded governance score (WGI or V-Dem) vs. ABS aggregate
    institutional trust, one point per country x wave. Convergent-validity check."""
    wave_year_map = wave_year_map or {}
    abs_agg = (
        abs_df.groupby(["country", "wave"])["trust_composite"]
        .mean()
        .reset_index()
        .rename(columns={"trust_composite": "abs_trust"})
    )
    abs_agg["year"] = abs_agg["wave"].map(lambda w: wave_year_map.get(w, w))
    abs_agg["year"] = pd.to_numeric(abs_agg["year"], errors="coerce")

    merged = abs_agg.merge(panel_df[["country", "year", expert_col]], on=["country", "year"], how="left")
    missing = merged[merged[expert_col].isna()]
    if len(missing) == len(merged):
        logger.warning(
            "no rows matched between ABS countries/years and the panel -- check that "
            "country spelling and the wave->year mapping line up."
        )
        return None, merged
    elif len(missing):
        logger.info(
            "%d/%d country-wave rows had no matching %s value in the panel (dropped from the plot).",
            len(missing),
            len(merged),
            expert_col,
        )
    merged = merged.dropna(subset=[expert_col])

    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    for wave, g in merged.groupby("wave"):
        ax.scatter(
            g[expert_col],
            g["abs_trust"],
            s=70,
            color=config.WAVE_COLORS.get(str(wave), "#999999"),
            label=str(wave),
            zorder=3,
        )
        for _, row in g.iterrows():
            ax.annotate(
                row["country"],
                (row[expert_col], row["abs_trust"]),
                fontsize=7.5,
                xytext=(4, 4),
                textcoords="offset points",
            )
    if len(merged) >= 3:
        r = merged[expert_col].corr(merged["abs_trust"])
        ax.set_title(
            f"ABS Aggregate Trust vs. {expert_label} (r={r:.2f}, n={len(merged)})",
            fontsize=11,
            loc="left",
            fontweight="bold",
        )
    else:
        ax.set_title(f"ABS Aggregate Trust vs. {expert_label}", fontsize=11, loc="left", fontweight="bold")
    ax.set_xlabel(expert_label)
    ax.set_ylabel("ABS Mean Institutional Trust (1-4)")
    ax.legend(frameon=False, title="Wave")
    fig.tight_layout()
    _save(fig, savepath)
    return fig, merged
