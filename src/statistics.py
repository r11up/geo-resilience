"""Generic statistical primitives: stationarity-gated Granger causality (single
series and pooled panel), Cronbach's alpha, and time-series forecasting +
backtesting. Ports notebook Sections 16a/16d, 18/20, and 21f (Cronbach's alpha
only) unchanged -- every threshold, seed-as-parameter, and formula is preserved
verbatim from ``nepal_south_asia_timeseries_V7.ipynb``.

Nothing in this module is paper-specific: functions take plain ``pandas``
Series/DataFrames and return numbers or small result dicts. Paper-specific
orchestration (which series get compared, with what labels) lives in
``src/analysis.py``.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import Holt
from statsmodels.tsa.stattools import adfuller, grangercausalitytests, kpss

logger = logging.getLogger("nepal_south_asia")


# ---------------------------------------------------------------------------
# Stationarity-gated Granger causality (single pair)
# ---------------------------------------------------------------------------


def stationarity_verdict(series: pd.Series, regression: str = "ct") -> dict[str, Any]:
    """ADF + KPSS stationarity check for one series.

    Both tests must agree the series is stationary (ADF rejects a unit root
    AND KPSS fails to reject stationarity) before it is called "stationary" --
    this conservative AND-gate is what ``safe_granger`` uses to decide whether
    to first-difference before testing for Granger causality.
    """
    s = series.dropna()
    _, adf_p, *_ = adfuller(s, autolag="AIC", regression=regression)
    try:
        _, kpss_p, *_ = kpss(s, regression=regression, nlags="auto")
    except Exception:
        kpss_p = np.nan
    adf_says_stationary = adf_p < 0.05
    kpss_says_stationary = (kpss_p > 0.05) if not np.isnan(kpss_p) else None
    if adf_says_stationary and kpss_says_stationary:
        verdict = "stationary"
    else:
        verdict = "non-stationary"
    return {
        "adf_p": round(adf_p, 4),
        "kpss_p": round(kpss_p, 4) if not np.isnan(kpss_p) else None,
        "verdict": verdict,
    }


def safe_granger(x: pd.Series, y: pd.Series, maxlag: int = 2, verbose: bool = True) -> tuple[dict[int, float], str]:
    """Stationarity-gated Granger test of ``x -> y``.

    Differences both series first if either is found non-stationary, to avoid
    the spurious-precedence risk of running a naive Granger test on two
    trending series (validated by the self-check in
    ``tests/test_basic.py``, ported from the notebook's own synthetic-data
    check on independent random walks).
    """
    df = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    vx, vy = stationarity_verdict(df["x"]), stationarity_verdict(df["y"])
    used = "levels"
    if vx["verdict"] == "non-stationary" or vy["verdict"] == "non-stationary":
        df = df.diff().dropna()
        used = "first-differenced"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = grangercausalitytests(df[["y", "x"]], maxlag=maxlag, verbose=False)
    pvals = {lag: round(res[lag][0]["ssr_ftest"][1], 4) for lag in res}
    if verbose:
        logger.info("  x stationarity: %s (ADF p=%s, KPSS p=%s)", vx["verdict"], vx["adf_p"], vx["kpss_p"])
        logger.info("  y stationarity: %s (ADF p=%s, KPSS p=%s)", vy["verdict"], vy["adf_p"], vy["kpss_p"])
        logger.info("  series used for the Granger test: %s", used)
    return pvals, used


# ---------------------------------------------------------------------------
# Panel (pooled) Granger causality -- Dumitrescu-Hurlin-style
# ---------------------------------------------------------------------------


def _wald_stat(df: pd.DataFrame, lag: int) -> float:
    """Wald statistic (``df_num * F``) for the ``x -> y`` Granger F-test at one lag."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = grangercausalitytests(df[["y", "x"]], maxlag=lag, verbose=False)
    F, pval, df_denom, df_num = res[lag][0]["ssr_ftest"]
    return df_num * F


def _prep_pair(x: pd.Series, y: pd.Series) -> pd.DataFrame:
    """Align one country's (x, y) pair and first-difference if either is non-stationary."""
    df = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    vx = stationarity_verdict(df["x"])["verdict"]
    vy = stationarity_verdict(df["y"])["verdict"]
    if vx == "non-stationary" or vy == "non-stationary":
        df = df.diff().dropna()
    return df


def panel_granger(
    country_series_pairs: dict[str, tuple[pd.Series, pd.Series]],
    lag: int = 1,
    n_boot: int = 2000,
    seed: int = 0,
    shift_min_frac: float = 0.2,
    verbose: bool = True,
) -> dict[str, Any] | None:
    """Dumitrescu-Hurlin-style pooled panel Granger test (x -> y).

    Reports both the classical asymptotic Z-bar p-value and a circular-shift
    permutation empirical p-value -- the latter is the one to trust at small N
    (this study pools across 6 countries).

    Parameters
    ----------
    country_series_pairs:
        ``{country: (x_series, y_series)}``.
    """
    rng = np.random.default_rng(seed)
    prepped = {
        c: _prep_pair(x, y) for c, (x, y) in country_series_pairs.items() if len(_prep_pair(x, y)) >= 2 * lag + 4
    }
    if len(prepped) < 3:
        if verbose:
            logger.info("  Only %d countries had enough overlapping data -- skipping.", len(prepped))
        return None

    obs_stats = {c: _wald_stat(df, lag) for c, df in prepped.items()}
    W_bar_obs = np.mean(list(obs_stats.values()))
    N = len(prepped)
    Z_bar = np.sqrt(N / (2 * lag)) * (W_bar_obs - lag)
    z_bar_p = 2 * (1 - norm.cdf(abs(Z_bar)))

    boot_wbars = np.zeros(n_boot)
    for b in range(n_boot):
        stats_b = []
        for c, df in prepped.items():
            n = len(df)
            min_shift = max(1, int(shift_min_frac * n))
            hi = max(min_shift + 1, n - min_shift)
            shift = rng.integers(min_shift, hi)
            x_shifted = np.roll(df["x"].values, shift)
            try:
                stats_b.append(_wald_stat(pd.DataFrame({"y": df["y"].values, "x": x_shifted}), lag))
            except Exception:
                stats_b.append(np.nan)
        boot_wbars[b] = np.nanmean(stats_b)
    emp_p = float(np.mean(boot_wbars >= W_bar_obs))

    from src.utils import country_name

    return {
        "n_countries": N,
        "per_country_wald": {country_name(c): round(v, 3) for c, v in obs_stats.items()},
        "W_bar": round(W_bar_obs, 4),
        "Z_bar_asymptotic": round(Z_bar, 4),
        "z_bar_p_asymptotic": round(z_bar_p, 4),
        "empirical_p_bootstrap": round(emp_p, 4),
    }


# ---------------------------------------------------------------------------
# Survey-scale reliability
# ---------------------------------------------------------------------------


def cronbach_alpha(item_df: pd.DataFrame) -> float:
    """Cronbach's alpha for a set of Likert-type items (rows = respondents)."""
    item_df = item_df.dropna()
    k = item_df.shape[1]
    if k < 2 or len(item_df) < 3:
        return np.nan
    item_vars = item_df.var(axis=0, ddof=1)
    total_var = item_df.sum(axis=1).var(ddof=1)
    return (k / (k - 1)) * (1 - item_vars.sum() / total_var)


# ---------------------------------------------------------------------------
# Forecasting models
# ---------------------------------------------------------------------------


def linear_trend_forecast(series: pd.Series, horizon: int = 5, alpha: float = 0.05) -> tuple[pd.DataFrame, Any]:
    """OLS linear-trend forecast with prediction intervals."""
    s = series.dropna()
    years = s.index.values.astype(float)
    X = sm.add_constant(years)
    model = sm.OLS(s.values, X).fit()
    future_years = np.arange(years.max() + 1, years.max() + horizon + 1)
    pred = model.get_prediction(sm.add_constant(future_years))
    frame = pred.summary_frame(alpha=alpha)
    return (
        pd.DataFrame(
            {
                "forecast": frame["mean"].values,
                "lower": frame["obs_ci_lower"].values,
                "upper": frame["obs_ci_upper"].values,
            },
            index=future_years.astype(int),
        ),
        model,
    )


def holt_forecast(series: pd.Series, horizon: int = 5) -> tuple[pd.Series, Any]:
    """Holt (double) exponential-smoothing forecast."""
    s = series.dropna()
    fit = Holt(s.values, initialization_method="estimated").fit(optimized=True)
    fc = fit.forecast(horizon)
    future_years = np.arange(s.index.max() + 1, s.index.max() + horizon + 1)
    return pd.Series(fc, index=future_years, name="holt_forecast"), fit


def small_grid_arima_forecast(
    series: pd.Series,
    horizon: int = 5,
    alpha: float = 0.05,
    max_p: int = 2,
    max_d: int = 1,
    max_q: int = 2,
) -> tuple[pd.DataFrame, tuple[int, int, int]]:
    """AIC-selected ARIMA forecast over a small (p, d, q) grid."""
    s = series.dropna()
    best_aic, best_order, best_fit = np.inf, None, None
    for p in range(max_p + 1):
        for d in range(max_d + 1):
            for q in range(max_q + 1):
                if p == 0 and q == 0:
                    continue
                try:
                    fit = ARIMA(s.values, order=(p, d, q)).fit()
                    if fit.aic < best_aic:
                        best_aic, best_order, best_fit = fit.aic, (p, d, q), fit
                except Exception:
                    continue
    if best_fit is None:
        raise RuntimeError("No ARIMA order converged for this series.")
    fc = best_fit.get_forecast(steps=horizon)
    frame = fc.summary_frame(alpha=alpha)
    future_years = np.arange(s.index.max() + 1, s.index.max() + horizon + 1)
    return (
        pd.DataFrame(
            {
                "forecast": frame["mean"].values,
                "lower": frame["mean_ci_lower"].values,
                "upper": frame["mean_ci_upper"].values,
            },
            index=future_years.astype(int),
        ),
        best_order,
    )


def backtest(series: pd.Series, holdout: int = 5, alpha: float = 0.05) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Fit each forecasting model through year ``T - holdout``, forecast
    ``holdout`` years ahead, and score against the actual held-out values.

    This is what makes the R^2/ARIMA numbers defensible as a historical-fit
    claim rather than just an in-sample fit.
    """
    s = series.dropna().sort_index()
    if len(s) < holdout + 8:
        logger.info(
            "  (only %d observations -- too few to hold out %d years and still fit sensibly; backtest skipped)",
            len(s),
            holdout,
        )
        return None
    train, test = s.iloc[:-holdout], s.iloc[-holdout:]
    rows = []
    lt, _ = linear_trend_forecast(train, horizon=holdout, alpha=alpha)
    hw, _ = holt_forecast(train, horizon=holdout)
    ar, order = small_grid_arima_forecast(train, horizon=holdout, alpha=alpha)
    for name, fc in [("Linear trend", lt), ("Holt", hw), (f"ARIMA{order}", ar)]:
        for yr, actual in test.items():
            if yr not in fc.index:
                continue
            point = fc.loc[yr, "forecast"] if hasattr(fc, "columns") else fc.loc[yr]
            has_ci = hasattr(fc, "columns") and "lower" in fc.columns
            in_band = float(fc.loc[yr, "lower"] <= actual <= fc.loc[yr, "upper"]) if has_ci else np.nan
            ape = abs((actual - point) / actual) * 100 if actual != 0 else np.nan
            rows.append(
                {
                    "model": name,
                    "year": yr,
                    "actual": actual,
                    "forecast": point,
                    "in_95pct_band": in_band,
                    "abs_pct_error": ape,
                }
            )
    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby("model")
        .agg(
            mean_abs_pct_error=("abs_pct_error", "mean"),
            coverage=("in_95pct_band", "mean"),
            n_years_tested=("year", "count"),
        )
        .round(3)
    )
    return detail, summary
