"""Paper-specific analysis orchestration: ties `config.py` constants and
`preprocessing.py`/`statistics.py` outputs together to produce the exact result
sets the notebook computes. Ports notebook Sections 7b, 16b/16d (application
halves), 18-20 (application halves), 21b, and 21n unchanged.

Where `statistics.py` holds generic, reusable statistical primitives (Granger
tests, forecasting models, Cronbach's alpha), this module holds the paper's own
choices about *which* series get compared, with what labels, and what that
means for the paper's argument -- i.e. "run the QA crosscheck," "test exit vs.
migration for Nepal," "run the CFA mediation model on the real ABS data."
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import semopy

from src import config, statistics
from src.plotting import plot_mediation_result

logger = logging.getLogger("nepal_south_asia")


# ---------------------------------------------------------------------------
# 7b -- internal QA: manually-downloaded WGI vs. V-Dem's bundled WGI estimates
# ---------------------------------------------------------------------------


def wgi_vdem_qa_crosscheck(panel: pd.DataFrame, verbose: bool = True) -> dict[str, float | None]:
    """Pearson r between the manually-downloaded WGI file and V-Dem's own
    bundled WGI estimates, per dimension, over overlapping country-years.

    Internal QA only -- not a paper-facing result. A low correlation here
    flags a parsing problem in ``preprocessing.load_wgi_manual`` or a
    country/year mismatch, not a real disagreement between two governance
    datasets (V-Dem's "Full+Others" release folds in the same World Bank WGI
    "Estimate" series as external variables, so these two SHOULD closely
    agree almost everywhere they both have data).
    """
    from src.utils import label_for

    results: dict[str, float | None] = {}
    for wgi_code, vdem_code in config.WGI_VS_VDEM_MAP.items():
        if wgi_code not in panel.columns or vdem_code not in panel.columns:
            results[wgi_code] = None
            if verbose:
                logger.info(
                    "  %-26s vs %-12s: one or both columns not in panel yet",
                    label_for(wgi_code, short=True),
                    vdem_code,
                )
            continue
        both = panel[[wgi_code, vdem_code]].dropna()
        if len(both) < 5:
            results[wgi_code] = None
            if verbose:
                logger.info(
                    "  %-26s vs %-12s: not enough overlapping rows to check yet",
                    label_for(wgi_code, short=True),
                    vdem_code,
                )
            continue
        r = both[wgi_code].corr(both[vdem_code])
        results[wgi_code] = round(float(r), 4)
        if verbose:
            flag = "" if r > 0.9 else "  <-- check this one, expected > ~0.9"
            logger.info(
                "  %-26s vs %-12s: r=%.3f over %d country-years%s",
                label_for(wgi_code, short=True),
                vdem_code,
                r,
                len(both),
                flag,
            )
    return results


# ---------------------------------------------------------------------------
# 16b -- single-country (Nepal) stationarity-gated Granger applications
# ---------------------------------------------------------------------------


def granger_exit_migration_nepal(
    panel: pd.DataFrame, maxlag: int = 2, verbose: bool = True
) -> dict[str, dict[int, float]] | None:
    """PRIMARY co-movement check: does freedom of foreign movement ("exit",
    ``v2clfmove``) precede realized net migration for Nepal, or vice versa?
    """
    nepal = panel[panel.iso3 == config.FOCAL].set_index("year").sort_index()
    if "v2clfmove" not in nepal.columns:
        logger.info("v2clfmove not in panel -- skipped.")
        return None
    g_exit = nepal[["v2clfmove", "SM.POP.NETM"]].dropna()
    if len(g_exit) < 8:
        logger.info("Not enough overlapping non-missing years -- skipped.")
        return None
    p_exit_xy, _ = statistics.safe_granger(g_exit["v2clfmove"], g_exit["SM.POP.NETM"], maxlag=maxlag, verbose=verbose)
    p_exit_yx, _ = statistics.safe_granger(g_exit["SM.POP.NETM"], g_exit["v2clfmove"], maxlag=maxlag, verbose=verbose)
    return {"exit_to_net_migration": p_exit_xy, "net_migration_to_exit": p_exit_yx}


def granger_corruption_remittances_nepal(
    panel: pd.DataFrame, maxlag: int = 2, verbose: bool = True
) -> dict[str, dict[int, float]] | None:
    """SECONDARY co-movement check: Control of Corruption vs. remittances (% GDP), Nepal."""
    nepal = panel[panel.iso3 == config.FOCAL].set_index("year").sort_index()
    g_df = nepal[["GOV_WGI_CC", "BX.TRF.PWKR.DT.GD.ZS"]].dropna()
    if len(g_df) < 8:
        logger.info("Not enough overlapping non-missing years -- skipped.")
        return None
    p_xy, _ = statistics.safe_granger(g_df["GOV_WGI_CC"], g_df["BX.TRF.PWKR.DT.GD.ZS"], maxlag=maxlag, verbose=verbose)
    p_yx, _ = statistics.safe_granger(g_df["BX.TRF.PWKR.DT.GD.ZS"], g_df["GOV_WGI_CC"], maxlag=maxlag, verbose=verbose)
    return {"corruption_to_remittances": p_xy, "remittances_to_corruption": p_yx}


# ---------------------------------------------------------------------------
# 16d -- pooled (panel) Granger applications, all 6 countries
# ---------------------------------------------------------------------------


def panel_granger_exit_migration(
    panel: pd.DataFrame, lag: int = 1, n_boot: int = 2000, seed: int = 42, verbose: bool = True
) -> dict[str, Any] | None:
    """PRIMARY pooled application: freedom of foreign movement ("exit") -> net migration."""
    real_pairs = {}
    for c in config.COUNTRIES:
        sub = panel[panel.iso3 == c].set_index("year").sort_index()
        if "v2clfmove" in sub.columns and "SM.POP.NETM" in sub.columns:
            real_pairs[c] = (sub["v2clfmove"], sub["SM.POP.NETM"])
    return statistics.panel_granger(real_pairs, lag=lag, n_boot=n_boot, seed=seed, verbose=verbose)


def panel_granger_corruption_remittances(
    panel: pd.DataFrame, lag: int = 1, n_boot: int = 2000, seed: int = 42, verbose: bool = True
) -> dict[str, Any] | None:
    """SECONDARY pooled application: Control of Corruption -> remittances (% GDP)."""
    real_pairs = {}
    for c in config.COUNTRIES:
        sub = panel[panel.iso3 == c].set_index("year").sort_index()
        if "GOV_WGI_CC" in sub.columns and "BX.TRF.PWKR.DT.GD.ZS" in sub.columns:
            real_pairs[c] = (sub["GOV_WGI_CC"], sub["BX.TRF.PWKR.DT.GD.ZS"])
    return statistics.panel_granger(real_pairs, lag=lag, n_boot=n_boot, seed=seed, verbose=verbose)


# ---------------------------------------------------------------------------
# 18-20 -- forecasting applications (linear trend + Holt + ARIMA + backtest)
# ---------------------------------------------------------------------------


def forecast_series_with_backtest(
    series: pd.Series, horizon: int = 5, holdout: int = 5, alpha: float = 0.05
) -> dict[str, Any]:
    """Runs all three forecasting models on ``series`` and backtests them.

    Used for both Figure E (Nepal remittances, % GDP) and Figure F (Nepal
    Government Effectiveness) -- the point of quoting these in the paper is
    the historical-fit quality (linear-trend R^2, backtest coverage/MAPE),
    not the forward projection itself (see notebook Section 17).
    """
    lt, lt_model = statistics.linear_trend_forecast(series, horizon=horizon, alpha=alpha)
    hw, hw_fit = statistics.holt_forecast(series, horizon=horizon)
    ar, ar_order = statistics.small_grid_arima_forecast(series, horizon=horizon, alpha=alpha)
    bt = statistics.backtest(series, holdout=holdout, alpha=alpha)
    return {
        "linear_trend": {"forecast": lt, "model": lt_model, "r_squared": lt_model.rsquared},
        "holt": {"forecast": hw, "model": hw_fit},
        "arima": {"forecast": ar, "order": ar_order},
        "backtest": bt,
    }


# ---------------------------------------------------------------------------
# 21g -- ABS trust-battery reliability
# ---------------------------------------------------------------------------


def abs_trust_reliability(abs_df: pd.DataFrame, verbose: bool = True) -> dict[str, dict[str, Any]]:
    """Cronbach's alpha for the trust battery, per ABS wave."""
    results: dict[str, dict[str, Any]] = {}
    for wave, g in abs_df.groupby("wave"):
        trust_cols = [c for c in g.columns if c.startswith("trust_item_") and g[c].notna().sum() > 10]
        a = statistics.cronbach_alpha(g[trust_cols])
        n_complete = g[trust_cols].dropna().shape[0]
        results[wave] = {"alpha": a, "n_items": len(trust_cols), "n_complete": n_complete}
        if verbose:
            flag = "" if (pd.isna(a) or a >= 0.7) else "  <-- below 0.7, treat the composite/CFA with caution"
            logger.info(
                "  wave %s: alpha=%.3f over %d items (n=%d complete respondents)%s",
                wave,
                a,
                len(trust_cols),
                n_complete,
                flag,
            )
    return results


# ---------------------------------------------------------------------------
# 21b -- CFA -> mediation -> bootstrapped indirect effect
# ---------------------------------------------------------------------------


def build_mediation_spec(
    trust_items: list[str], condition_col: str = "objective_condition", outcome_col: str = "migration_outcome"
) -> str:
    """lavaan-style model description: Trust as a latent variable measured by
    ``trust_items``, mediating between ``condition_col`` and ``outcome_col``.
    """
    loadings = " + ".join(trust_items)
    return f"""
Trust =~ {loadings}
{outcome_col} ~ Trust + {condition_col}
Trust ~ {condition_col}
"""


def run_mediation(
    df: pd.DataFrame,
    trust_items: list[str],
    condition_col: str = "objective_condition",
    outcome_col: str = "migration_outcome",
    n_boot: int = 1000,
    seed: int = 0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fits the CFA + path model, then bootstraps the indirect effect
    (condition -> Trust -> outcome) for a percentile CI.
    """
    required = list(trust_items) + [condition_col, outcome_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"mediation_df is missing required column(s): {missing}")
    if len(df.dropna(subset=required)) < 50:
        raise ValueError(
            f"Only {len(df.dropna(subset=required))} complete rows -- too few for a " "stable CFA + path model."
        )

    desc = build_mediation_spec(trust_items, condition_col, outcome_col)
    model = semopy.Model(desc)
    model.fit(df)
    params = model.inspect()

    rng = np.random.default_rng(seed)
    boots, n = [], len(df)
    for _ in range(n_boot):
        sample = df.iloc[rng.integers(0, n, n)].reset_index(drop=True)
        try:
            m = semopy.Model(desc)
            m.fit(sample)
            ins = m.inspect()
            a = ins[(ins["lval"] == "Trust") & (ins["rval"] == condition_col)]["Estimate"].values[0]
            b = ins[(ins["lval"] == outcome_col) & (ins["rval"] == "Trust")]["Estimate"].values[0]
            boots.append(a * b)
        except Exception:
            continue
    boots_arr = np.array(boots)
    indirect_summary = {
        "indirect_effect_mean": float(boots_arr.mean()) if len(boots_arr) else np.nan,
        "ci_2.5": float(np.percentile(boots_arr, 2.5)) if len(boots_arr) else np.nan,
        "ci_97.5": float(np.percentile(boots_arr, 97.5)) if len(boots_arr) else np.nan,
        "n_successful_bootstraps": len(boots_arr),
        "boot_samples": boots_arr,
        "significant": bool(
            len(boots_arr) and not (np.percentile(boots_arr, 2.5) < 0 < np.percentile(boots_arr, 97.5))
        ),
    }
    return params, indirect_summary


# ---------------------------------------------------------------------------
# 21n -- the real mediation model, run per subset x outcome x wave
# ---------------------------------------------------------------------------


def run_mediation_for_subset(
    df_subset: pd.DataFrame,
    outcome_col: str,
    label: str,
    n_boot: int = 1000,
    seed: int = 0,
    figures_dir: Path | None = None,
    make_plots: bool = True,
) -> dict[str, tuple[pd.DataFrame, dict[str, Any]]]:
    """Runs the CFA -> mediation -> bootstrap pipeline separately per wave on
    ``df_subset`` (already filtered to whichever countries you want), for one
    outcome column. Returns ``{wave: (params, indirect)}``.
    """
    figures_dir = figures_dir if figures_dir is not None else config.FIGURES_DIR
    mediation_results: dict[str, tuple[pd.DataFrame, dict[str, Any]]] = {}
    for wave, g in df_subset.groupby("wave"):
        trust_cols = [c for c in g.columns if c.startswith("trust_item_") and g[c].notna().sum() > 0]
        med_df = g[trust_cols + ["condition_composite", outcome_col]].rename(
            columns={"condition_composite": "objective_condition", outcome_col: "migration_outcome"}
        )
        n_complete = len(med_df.dropna())
        logger.info(
            "=== %s -- Wave %s, outcome=%s: %d complete respondents across %d trust items ===",
            label,
            wave,
            outcome_col,
            n_complete,
            len(trust_cols),
        )
        if n_complete < 50:
            logger.info("  Skipped -- fewer than 50 complete rows.")
            continue
        params, indirect = run_mediation(
            med_df,
            trust_items=trust_cols,
            condition_col="objective_condition",
            outcome_col="migration_outcome",
            n_boot=n_boot,
            seed=seed,
        )
        mediation_results[wave] = (params, indirect)
        logger.info(
            "  indirect effect (perceived condition -> Trust -> %s): %.3f, 95%% CI [%.3f, %.3f], significant=%s",
            outcome_col,
            indirect["indirect_effect_mean"],
            indirect["ci_2.5"],
            indirect["ci_97.5"],
            indirect["significant"],
        )
        if make_plots:
            safe_label = label.lower().replace(" ", "_").replace("(", "").replace(")", "")
            savepath = figures_dir / f"fig_mediation_{safe_label}_{outcome_col}_{wave}.png"
            plot_mediation_result(
                params,
                indirect,
                "objective_condition",
                "migration_outcome",
                condition_label="Perceived National\nCondition",
                outcome_label=config.OUTCOME_DISPLAY.get(outcome_col, outcome_col),
                title_suffix=f" -- {label}, Wave {wave}",
                savepath=savepath,
            )
    if len(mediation_results) == 2:
        waves_sorted = sorted(mediation_results)
        same_sign = np.sign(mediation_results[waves_sorted[0]][1]["indirect_effect_mean"]) == np.sign(
            mediation_results[waves_sorted[1]][1]["indirect_effect_mean"]
        )
        both_sig = all(mediation_results[w][1]["significant"] for w in waves_sorted)
        logger.info(
            "%s (%s) across-wave check: same direction in both waves = %s, significant in both waves = %s.",
            label,
            outcome_col,
            same_sign,
            both_sig,
        )
    return mediation_results
