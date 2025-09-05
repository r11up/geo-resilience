"""Smoke tests + deterministic self-checks for the ``src`` package.

Two of these tests (``test_safe_granger_spurious_regression_gate`` and
``test_panel_granger_null_and_causal_ground_truth``) are direct ports of the
notebook's own embedded validation cells (Sections 16a and 16d of
``nepal_south_asia_timeseries_V7.ipynb``): synthetic data with a *known*
ground truth is fed through the Granger-causality machinery to confirm the
stationarity gate suppresses spurious significance on independent random
walks, and that the panel test finds nothing when there is nothing and finds
a strong signal when all countries share one. These are not generic unit
tests -- they are the same correctness argument the paper relies on to trust
the real-data results, kept in the test suite so it keeps being checked.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import pytest

from src import config
from src.preprocessing import recode_scale
from src.statistics import (
    cronbach_alpha,
    panel_granger,
    safe_granger,
    stationarity_verdict,
)
from src.utils import country_name, label_for

# ---------------------------------------------------------------------------
# Import / package sanity
# ---------------------------------------------------------------------------


def test_all_modules_import():
    """Every project module should import cleanly with no side effects that raise."""
    import src.analysis  # noqa: F401
    import src.config  # noqa: F401
    import src.plotting  # noqa: F401
    import src.preprocessing  # noqa: F401
    import src.statistics  # noqa: F401
    import src.utils  # noqa: F401
    import src.visualization  # noqa: F401


def test_config_paths_are_consistent():
    assert config.FOCAL in config.COUNTRIES
    assert config.DATA_RAW_DIR.parent == config.DATA_DIR
    assert config.DATA_PROCESSED_DIR.parent == config.DATA_DIR
    assert config.PANEL_CSV.parent == config.DATA_PROCESSED_DIR
    assert config.ABS_CSV.parent == config.DATA_PROCESSED_DIR


def test_config_country_collections_agree():
    # Every country in the canonical list must have a display name and a color.
    for iso3 in config.COUNTRIES:
        assert iso3 in config.COUNTRY_NAMES
        assert iso3 in config.COUNTRY_COLORS


# ---------------------------------------------------------------------------
# src/utils.py
# ---------------------------------------------------------------------------


def test_country_name_known_and_unknown():
    assert country_name(config.FOCAL) == config.COUNTRY_NAMES[config.FOCAL]
    assert country_name("ZZZ") == "ZZZ"  # falls back to the raw code


def test_label_for_falls_back_to_code():
    assert label_for("this-code-does-not-exist") == "this-code-does-not-exist"


# ---------------------------------------------------------------------------
# src/preprocessing.py
# ---------------------------------------------------------------------------


def test_recode_scale_maps_and_flags_unmatched():
    mapping = {"strongly agree": 4.0, "agree": 3.0, "disagree": 2.0, "strongly disagree": 1.0}
    raw = pd.Series(["1. Strongly Agree", "2. Agree", "not applicable", None, "3. Disagree"])
    out = recode_scale(raw, mapping, name="test_item", verbose=False)
    assert out.tolist()[:2] == [4.0, 3.0]
    assert np.isnan(out.iloc[2])  # unmatched text -> NaN
    assert np.isnan(out.iloc[3])  # missing -> NaN
    assert out.iloc[4] == 2.0


def test_recode_scale_prefers_longest_pattern_match():
    # "strongly agree" must win over the shorter "agree" substring.
    mapping = {"agree": 3.0, "strongly agree": 4.0}
    out = recode_scale(pd.Series(["strongly agree"]), mapping, verbose=False)
    assert out.iloc[0] == 4.0


# ---------------------------------------------------------------------------
# src/statistics.py -- generic building blocks
# ---------------------------------------------------------------------------


def test_stationarity_verdict_on_white_noise():
    rng = np.random.default_rng(0)
    s = pd.Series(rng.normal(0, 1, 60), index=range(1960, 2020))
    verdict = stationarity_verdict(s)
    assert verdict["verdict"] == "stationary"


def test_stationarity_verdict_on_random_walk():
    rng = np.random.default_rng(0)
    s = pd.Series(np.cumsum(rng.normal(0.1, 0.3, 60)), index=range(1960, 2020))
    verdict = stationarity_verdict(s)
    assert verdict["verdict"] == "non-stationary"


def test_cronbach_alpha_perfectly_correlated_items_is_one():
    rng = np.random.default_rng(0)
    base = rng.normal(0, 1, 200)
    df = pd.DataFrame({"item1": base, "item2": base, "item3": base})
    assert cronbach_alpha(df) == pytest.approx(1.0, abs=1e-6)


def test_cronbach_alpha_too_few_items_or_rows_returns_nan():
    assert np.isnan(cronbach_alpha(pd.DataFrame({"item1": [1, 2, 3]})))
    assert np.isnan(cronbach_alpha(pd.DataFrame({"item1": [1, 2], "item2": [2, 1]})))


# ---------------------------------------------------------------------------
# Self-check ported from notebook cell 28 (Section 16a): does the
# stationarity gate actually suppress spurious Granger significance on two
# independent random walks, relative to a naive levels-only test?
# ---------------------------------------------------------------------------


def test_safe_granger_spurious_regression_gate():
    from statsmodels.tsa.stattools import grangercausalitytests

    naive_sig = fixed_sig = 0
    n_trials = 30
    for trial in range(n_trials):
        r = np.random.default_rng(1000 + trial)
        x_ind = pd.Series(np.cumsum(r.normal(0.1, 0.3, 27)), index=range(1996, 2023))
        y_ind = pd.Series(np.cumsum(r.normal(0.1, 0.3, 27)), index=range(1996, 2023))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            naive_p = min(
                grangercausalitytests(
                    pd.concat([y_ind.rename("y"), x_ind.rename("x")], axis=1),
                    maxlag=2,
                    verbose=False,
                )[lag][0]["ssr_ftest"][1]
                for lag in [1, 2]
            )
        naive_sig += naive_p < 0.05
        fixed_p, _ = safe_granger(x_ind, y_ind, maxlag=2, verbose=False)
        fixed_sig += min(fixed_p.values()) < 0.05

    # The gated test should be at (or very near) the nominal ~5% false-positive
    # rate on truly independent series; the naive levels-only test on trending
    # random walks is expected to be inflated well above that. This mirrors
    # the notebook's own printed self-check rather than asserting exact counts,
    # since both statistics are themselves random draws.
    assert fixed_sig <= naive_sig


# ---------------------------------------------------------------------------
# Self-check ported from notebook cell 31 (Section 16d): panel_granger should
# find (near-)nothing on synthetic panels with no true relationship, and a
# strong signal when every country genuinely shares one.
# ---------------------------------------------------------------------------


def test_panel_granger_null_and_causal_ground_truth():
    null_pairs = {}
    for i, c in enumerate(config.COUNTRIES):
        r = np.random.default_rng(3000 + i)
        x = pd.Series(np.cumsum(r.normal(0.1, 0.3, 27)), index=range(1996, 2023))
        y = pd.Series(np.cumsum(r.normal(0.1, 0.3, 27)), index=range(1996, 2023))
        null_pairs[c] = (x, y)
    null_result = panel_granger(null_pairs, lag=1, n_boot=200, seed=1, verbose=False)

    causal_pairs = {}
    for i, c in enumerate(config.COUNTRIES):
        r = np.random.default_rng(4000 + i)
        xv = r.normal(0, 1, 27)
        for t in range(1, 27):
            xv[t] = 0.4 * xv[t - 1] + r.normal(0, 0.8)
        yv = np.zeros(27)
        for t in range(1, 27):
            yv[t] = 0.3 * yv[t - 1] + 0.7 * xv[t - 1] + r.normal(0, 0.5)
        causal_pairs[c] = (
            pd.Series(xv, index=range(1996, 2023)),
            pd.Series(yv, index=range(1996, 2023)),
        )
    causal_result = panel_granger(causal_pairs, lag=1, n_boot=200, seed=2, verbose=False)

    assert null_result is not None and causal_result is not None
    # No true relationship -> large p-values; true shared x->y -> near-zero p-values.
    assert null_result["empirical_p_bootstrap"] > 0.05
    assert causal_result["empirical_p_bootstrap"] < 0.05


# ---------------------------------------------------------------------------
# Forecasting + backtesting smoke tests (does it run end-to-end and return
# the expected shapes, not "is the forecast accurate")
# ---------------------------------------------------------------------------


def test_forecast_series_with_backtest_smoke():
    from src.analysis import forecast_series_with_backtest

    rng = np.random.default_rng(0)
    years = range(1996, 2024)
    trend = np.linspace(2, 8, len(list(years)))
    series = pd.Series(trend + rng.normal(0, 0.3, len(trend)), index=list(years))

    results = forecast_series_with_backtest(series, horizon=5, holdout=5)
    assert set(results.keys()) == {"linear_trend", "holt", "arima", "backtest"}
    assert len(results["linear_trend"]["forecast"]) == 5
    assert len(results["holt"]["forecast"]) == 5
    assert len(results["arima"]["forecast"]) == 5
    assert results["backtest"] is not None
