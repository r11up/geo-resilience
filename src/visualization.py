"""Paper-figure orchestrators: one function per named figure in the paper,
each tying together ``config.py`` constants, ``analysis.py`` results, and
``plotting.py`` chart primitives, and saving the output under ``figures/``.

Ports notebook Sections 12, 12b, 12c, 13, 14, 16b (heatmap half), 19, 20,
21h-21o unchanged. Function names mirror the notebook's own figure labels
(Figure A, B, C, ... and the ABS figures) so the paper-figure <-> code mapping
stays traceable -- see ``README.md`` for the full figure/section map.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src import analysis, config, plotting
from src.utils import label_for


def figure_a_governance_trends(panel: pd.DataFrame, savepath: str | Path | None = None):
    """Figure A -- WGI governance/trust trends, Nepal vs. South Asia."""
    savepath = savepath or config.FIGURES_DIR / "fig_a_governance_trends.png"
    gov_cols = [(c, lbl) for c, lbl in config.WGI_INDICATORS.items()]
    return plotting.plot_trend_panel(
        panel,
        gov_cols,
        title="Worldwide Governance Indicators, Nepal vs. South Asia (1996-2024)",
        savepath=savepath,
    )


def figure_a2_vdem_trends(panel: pd.DataFrame, savepath: str | Path | None = None):
    """Figure A2 -- V-Dem governance & civic-space trends."""
    savepath = savepath or config.FIGURES_DIR / "fig_a2_vdem_trends.png"
    vdem_plot_cols = [
        ("v2x_libdem", "Liberal Democracy Index"),
        ("v2x_corr", "Political Corruption Index"),
        ("v2clfmove", "Freedom of Foreign Movement (exit option)"),
        ("v2xcs_ccsi", "Core Civil Society Index"),
    ]
    vdem_plot_cols = [(c, lbl) for c, lbl in vdem_plot_cols if c in panel.columns]
    if not vdem_plot_cols:
        return None
    return plotting.plot_trend_panel(
        panel,
        vdem_plot_cols,
        ncols=2,
        title="V-Dem Governance & Civic Space, Nepal vs. South Asia",
        savepath=savepath,
    )


def figure_g_democratic_resilience(panel: pd.DataFrame, savepath: str | Path | None = None):
    """Figure G -- Democratic Resilience (V-Dem Regimes of the World). Fig. 2's own terminal node."""
    savepath = savepath or config.FIGURES_DIR / "fig_g_democratic_resilience_regime.png"
    return plotting.plot_regime_trajectory(panel, regime_col="v2x_regime", savepath=savepath)


def figure_c_socioeconomic_trends(panel: pd.DataFrame, savepath: str | Path | None = None):
    """Figure C -- socio-economic trends (GDP/capita, enrollment, youth unemployment)."""
    savepath = savepath or config.FIGURES_DIR / "fig_c_socioeconomic_trends.png"
    socio_cols = [(c, lbl) for c, lbl in config.SOCIOECON_INDICATORS.items()]
    return plotting.plot_trend_panel(
        panel,
        socio_cols,
        title="Socio-economic Trends, Nepal vs. South Asia",
        savepath=savepath,
    )


def figure_b_migration_trends(panel: pd.DataFrame, savepath: str | Path | None = None):
    """Figure B -- migration/remittance trends. Migrant stock uses the
    linearly-interpolated ``SM.POP.TOTL_filled`` column for plotting only
    (see ``preprocessing.build_master_panel``) -- the raw 5-year-only
    ``SM.POP.TOTL`` series otherwise renders as blank."""
    savepath = savepath or config.FIGURES_DIR / "fig_b_migration_trends.png"
    mig_cols = []
    for c, lbl in config.MIGRATION_INDICATORS.items():
        fmt_hint = "big_number" if c in config.BIG_NUMBER_INDICATORS else None
        if c == "SM.POP.TOTL":
            mig_cols.append(("SM.POP.TOTL_filled", lbl + " (interpolated between 5-yr checkpoints)", fmt_hint))
        else:
            mig_cols.append((c, lbl, fmt_hint))
    return plotting.plot_trend_panel(
        panel,
        mig_cols,
        ncols=2,
        title="Migration & Remittance Trends, Nepal vs. South Asia",
        savepath=savepath,
    )


def figure_d_correlation_heatmap(panel: pd.DataFrame, savepath: str | Path | None = None) -> tuple[Any, pd.DataFrame]:
    """Figure D -- Nepal exit/governance/migration-proxy co-movement heatmap."""
    savepath = savepath or config.FIGURES_DIR / "fig_d_correlation_heatmap.png"
    nepal = panel[panel.iso3 == config.FOCAL].set_index("year").sort_index()
    corr_cols = ["GOV_WGI_VA", "GOV_WGI_CC", "v2clfmove", "BX.TRF.PWKR.DT.GD.ZS", "SM.POP.NETM"]
    corr_cols = [c for c in corr_cols if c in nepal.columns]
    corr = nepal[corr_cols].corr()
    readable = [label_for(c, short=True) for c in corr_cols]
    corr_display = corr.copy()
    corr_display.index = readable
    corr_display.columns = readable
    fig = plotting.plot_correlation_heatmap(
        corr_display,
        title="Nepal: exit, governance & migration-proxy co-movement",
        ylabel_note="Pearson r (Nepal, country-year)",
        savepath=savepath,
    )
    return fig, corr_display


def figure_e_remittances_forecast(
    panel: pd.DataFrame, savepath: str | Path | None = None
) -> tuple[Any, dict[str, Any]]:
    """Figure E -- Nepal remittances (% GDP): observed + 3 forecasts + backtest.

    The number to quote in the paper is the linear-trend R^2 (historical-fit
    quality), not the 2029 forecast endpoint -- see notebook Section 17.
    """
    savepath = savepath or config.FIGURES_DIR / "fig_e_remittances_forecast.png"
    nepal = panel[panel.iso3 == config.FOCAL].set_index("year").sort_index()
    hist = nepal["BX.TRF.PWKR.DT.GD.ZS"].dropna()
    results = analysis.forecast_series_with_backtest(hist, horizon=5, holdout=5)
    forecasts_dict = {
        "Linear trend": results["linear_trend"]["forecast"],
        "Holt": results["holt"]["forecast"],
        f"ARIMA{results['arima']['order']}": results["arima"]["forecast"],
    }
    fig = plotting.plot_forecast_fan(
        hist,
        forecasts_dict,
        ylabel="Remittances Received (% of GDP)",
        title="Nepal: Remittances (% of GDP) — Observed & 5-Year Forecast",
        savepath=savepath,
    )
    return fig, results


def figure_f_governance_forecast(panel: pd.DataFrame, savepath: str | Path | None = None) -> tuple[Any, dict[str, Any]]:
    """Figure F -- Nepal Government Effectiveness (WGI): observed + 3 forecasts + backtest."""
    savepath = savepath or config.FIGURES_DIR / "fig_f_governance_forecast.png"
    nepal = panel[panel.iso3 == config.FOCAL].set_index("year").sort_index()
    hist = nepal["GOV_WGI_GE"].dropna()
    results = analysis.forecast_series_with_backtest(hist, horizon=5, holdout=5)
    forecasts_dict = {
        "Linear trend": results["linear_trend"]["forecast"],
        "Holt": results["holt"]["forecast"],
        f"ARIMA{results['arima']['order']}": results["arima"]["forecast"],
    }
    fig = plotting.plot_forecast_fan(
        hist,
        forecasts_dict,
        ylabel="Government Effectiveness (WGI estimate, ~ -2.5 to 2.5)",
        title="Nepal: Government Effectiveness — Observed & 5-Year Forecast",
        savepath=savepath,
    )
    return fig, results


def figure_abs_trust_wave(abs_df: pd.DataFrame, savepath: str | Path | None = None):
    """Institutional trust by country, 2005 vs. 2013 (Asian Barometer)."""
    savepath = savepath or config.FIGURES_DIR / "fig_abs_trust_wave.png"
    return plotting.plot_wave_comparison(
        abs_df,
        "trust_composite",
        "Mean Institutional Trust (1-4 scale)",
        "Institutional Trust by Country, 2005 vs. 2013 (Asian Barometer)",
        country_order=config.ABS_COUNTRY_ORDER,
        savepath=savepath,
    )


def figure_abs_trust_by_institution(
    abs_df: pd.DataFrame,
    wave_label: str,
    trust_items: list[str],
    trust_labels: dict[str, str],
    savepath: str | Path | None = None,
):
    """Institution-level trust breakdown for ONE ABS wave (called once per wave)."""
    savepath = savepath or config.FIGURES_DIR / f"fig_abs_trust_institution_{wave_label}.png"
    wave_df = abs_df[abs_df["wave"] == wave_label]
    trust_cols = [f"trust_item_{i}" for i in range(len(trust_items))]
    labels = dict(zip(trust_cols, [trust_labels[c] for c in trust_items]))
    return plotting.plot_trust_by_institution(wave_df, trust_cols, labels, wave_label, savepath=savepath)


def figure_abs_regime_wave(abs_df: pd.DataFrame, savepath: str | Path | None = None):
    """Regime preference (support for democracy) by country, 2005 vs. 2013."""
    savepath = savepath or config.FIGURES_DIR / "fig_abs_regime_wave.png"
    return plotting.plot_wave_comparison(
        abs_df,
        "regime_preference",
        "Mean Pro-Democracy Preference (1=Authoritarian-OK .. 3=Always-Prefer-Democracy)",
        "Regime Preference by Country, 2005 vs. 2013 (Asian Barometer)",
        country_order=config.ABS_COUNTRY_ORDER,
        savepath=savepath,
    )


def figure_abs_condition_wave(abs_df: pd.DataFrame, savepath: str | Path | None = None):
    """Perceived economic/national condition by country, 2005 vs. 2013.

    Closest available individual-level proxy for the Perceived Opportunity
    Landscape (Definition 1.1).
    """
    savepath = savepath or config.FIGURES_DIR / "fig_abs_condition_wave.png"
    return plotting.plot_wave_comparison(
        abs_df,
        "condition_composite",
        "Mean Perceived Condition (z-scored composite; higher = better/improving)",
        "Perceived Conditions by Country, 2005 vs. 2013 (Asian Barometer)",
        country_order=config.ABS_COUNTRY_ORDER,
        savepath=savepath,
    )


def figure_abs_problem_solving_expectation(
    abs_df: pd.DataFrame, savepath: str | Path | None = None
) -> tuple[Any, pd.DataFrame] | None:
    """GBC32, government problem-solving expectation (Wave 2 / 2013 only) --
    this notebook's closest empirical analog for Endsley's "projection" stage."""
    import matplotlib.pyplot as plt

    if "extra_item_raw" not in abs_df.columns or not abs_df["extra_item_raw"].notna().any():
        return None
    savepath = savepath or config.FIGURES_DIR / "fig_abs_problem_solving_expectation.png"
    cand = abs_df[abs_df["wave"] == "2013"].groupby("country")["extra_item_raw"].agg(["mean", "count"])
    order = config.ABS_COUNTRY_ORDER
    vals = cand.reindex(order)["mean"]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.bar(vals.index, vals.values, color="#C98A2C")
    ax.set_ylabel("Mean Likelihood Government Solves Top Problem (1-4)")
    ax.set_title(
        'Government Problem-Solving Expectation by Country, 2013\n(the "projection" stage, Section 3.3)',
        fontsize=11,
        loc="left",
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(savepath, bbox_inches="tight")
    return fig, cand


def figure_triangulation(
    abs_df: pd.DataFrame, panel: pd.DataFrame, savepath: str | Path | None = None
) -> tuple[Any, pd.DataFrame]:
    """Does ABS's individual-level aggregate trust track the expert-coded
    governance panel for the same country-years? A convergent-validity check,
    not a forecast and not a substitute for either one."""
    savepath = savepath or config.FIGURES_DIR / "fig_abs_vs_wgi_triangulation.png"
    return plotting.plot_abs_vs_expert_governance(
        abs_df,
        panel,
        "GOV_WGI_GE",
        label_for("GOV_WGI_GE"),
        wave_year_map={"2005": 2005, "2013": 2013},
        savepath=savepath,
    )
