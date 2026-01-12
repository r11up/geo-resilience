#!/usr/bin/env python
"""Canonical end-to-end pipeline: load raw data -> preprocess -> analyze ->
generate figures -> save outputs.

This is the single command that reproduces every figure and numeric result in
"Public Trust and Geo Spatial Resilience" from the manually
downloaded raw files described in ``data/README.md``.

Usage
-----
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --raw-dir /path/to/raw --skip-mediation
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import analysis, config, preprocessing, visualization
from src.utils import ensure_dir, setup_logging


def check_raw_files(raw_dir: Path) -> dict[str, Path]:
    """Verify the four manually-downloaded raw files are present, and return their paths.

    Raises ``FileNotFoundError`` with a pointer to ``data/README.md`` if any are missing --
    these files cannot be fetched automatically (see README for why).
    """
    expected = {
        "wgi": raw_dir / config.WGI_RAW_PATH.name,
        "vdem": raw_dir / config.VDEM_RAW_PATH.name,
        "abs_wave1": raw_dir / config.ABS_WAVE1_RAW_PATH.name,
        "abs_wave2": raw_dir / config.ABS_WAVE2_RAW_PATH.name,
    }
    missing = [str(p) for p in expected.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required raw data file(s):\n  "
            + "\n  ".join(missing)
            + "\n\nThese must be downloaded manually -- see data/README.md for exact "
            "sources and instructions, then place them under data/raw/."
        )
    return expected


def run_preprocessing(raw_dir: Path, logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load all raw sources, build the master country-year panel and the ABS
    respondent-level frame, and save both to ``data/processed/``.
    """
    raw_files = check_raw_files(raw_dir)

    logger.info("Loading WGI (manual file)...")
    wgi_long = preprocessing.load_wgi_manual(raw_files["wgi"], countries=config.COUNTRIES)

    logger.info("Loading V-Dem (manual file, column subset)...")
    vdem_long = preprocessing.load_vdem_manual(
        raw_files["vdem"],
        list(config.VDEM_INDICATORS.keys()),
        countries=config.COUNTRIES,
        start_year=config.WDI_START,
        end_year=config.WDI_END,
    )

    logger.info("Fetching migration & socio-economic indicators from the World Bank API...")
    migration_long = preprocessing.fetch_worldbank(
        config.COUNTRIES, list(config.MIGRATION_INDICATORS.keys()), config.WDI_START, config.WDI_END
    )
    socioecon_long = preprocessing.fetch_worldbank(
        config.COUNTRIES, list(config.SOCIOECON_INDICATORS.keys()), config.WDI_START, config.WDI_END
    )

    logger.info("Building master country-year panel...")
    panel = preprocessing.build_master_panel(wgi_long, vdem_long, migration_long, socioecon_long)
    logger.info("Master panel shape: %s", panel.shape)

    logger.info("Loading Asian Barometer waves 1 (2005) and 2 (2013)...")
    abs_df = preprocessing.load_abs_waves(raw_files["abs_wave1"], raw_files["abs_wave2"])
    logger.info("ABS respondent-level shape: %s", abs_df.shape)

    ensure_dir(config.DATA_PROCESSED_DIR)
    panel.to_csv(config.PANEL_CSV, index=False)
    abs_df.to_csv(config.ABS_CSV, index=False)
    logger.info("Saved panel -> %s", config.PANEL_CSV)
    logger.info("Saved ABS respondent-level data -> %s", config.ABS_CSV)
    return panel, abs_df


def run_analysis(panel: pd.DataFrame, abs_df: pd.DataFrame, logger, skip_mediation: bool = False) -> dict[str, Any]:
    """Run every non-plotting analysis: QA crosscheck, Granger (single + panel),
    forecasting/backtesting, ABS reliability, and (unless skipped) the CFA
    mediation model.
    """
    results: dict[str, Any] = {}

    logger.info("=== Internal QA: manual WGI vs. V-Dem-bundled WGI ===")
    results["wgi_vdem_qa"] = analysis.wgi_vdem_qa_crosscheck(panel)

    logger.info("=== PRIMARY Granger: exit (v2clfmove) <-> net migration, Nepal ===")
    results["granger_exit_migration"] = analysis.granger_exit_migration_nepal(panel)

    logger.info("=== SECONDARY Granger: corruption <-> remittances, Nepal ===")
    results["granger_corruption_remittances"] = analysis.granger_corruption_remittances_nepal(panel)

    logger.info("=== PRIMARY panel Granger: exit -> net migration, pooled ===")
    results["panel_granger_exit_migration"] = analysis.panel_granger_exit_migration(panel)

    logger.info("=== SECONDARY panel Granger: corruption -> remittances, pooled ===")
    results["panel_granger_corruption_remittances"] = analysis.panel_granger_corruption_remittances(panel)

    logger.info("=== ABS trust-battery reliability (Cronbach's alpha) ===")
    results["abs_trust_reliability"] = analysis.abs_trust_reliability(abs_df)

    if not skip_mediation:
        logger.info("=== Mediation: Nepal-only, outcome = regime preference (PRIMARY) ===")
        nepal_only = abs_df[abs_df["country"] == "Nepal"]
        results["mediation_nepal_regime"] = analysis.run_mediation_for_subset(
            nepal_only, "regime_preference", "Nepal-only"
        )
        logger.info("=== Mediation: Nepal-only, outcome = satisfaction with democracy (robustness) ===")
        results["mediation_nepal_satisfaction"] = analysis.run_mediation_for_subset(
            nepal_only, "satisfaction_democracy", "Nepal-only"
        )
        logger.info("=== Mediation: pooled 5-country, outcome = regime preference (RQ4) ===")
        results["mediation_pooled_regime"] = analysis.run_mediation_for_subset(
            abs_df, "regime_preference", "Pooled-5-country"
        )
    else:
        logger.info("Skipping mediation models (--skip-mediation).")

    return results


def run_visualization(panel: pd.DataFrame, abs_df: pd.DataFrame, logger) -> None:
    """Generate every named figure and save it under ``figures/``."""
    ensure_dir(config.FIGURES_DIR)

    logger.info("Figure A -- WGI governance trends")
    visualization.figure_a_governance_trends(panel)

    logger.info("Figure A2 -- V-Dem governance & civic-space trends")
    visualization.figure_a2_vdem_trends(panel)

    logger.info("Figure G -- Democratic Resilience (V-Dem Regimes of the World)")
    visualization.figure_g_democratic_resilience(panel)

    logger.info("Figure C -- socio-economic trends")
    visualization.figure_c_socioeconomic_trends(panel)

    logger.info("Figure B -- migration & remittance trends")
    visualization.figure_b_migration_trends(panel)

    logger.info("Figure D -- Nepal correlation heatmap")
    visualization.figure_d_correlation_heatmap(panel)

    logger.info("Figure E -- Nepal remittances forecast")
    visualization.figure_e_remittances_forecast(panel)

    logger.info("Figure F -- Nepal governance forecast")
    visualization.figure_f_governance_forecast(panel)

    logger.info("ABS trust-by-wave figure")
    visualization.figure_abs_trust_wave(abs_df)

    logger.info("ABS institution-level trust figures (2005, 2013)")
    visualization.figure_abs_trust_by_institution(abs_df, "2005", config.WAVE1_TRUST_ITEMS, config.WAVE1_TRUST_LABELS)
    visualization.figure_abs_trust_by_institution(abs_df, "2013", config.WAVE2_TRUST_ITEMS, config.WAVE2_TRUST_LABELS)

    logger.info("ABS regime-preference-by-wave figure")
    visualization.figure_abs_regime_wave(abs_df)

    logger.info("ABS perceived-condition-by-wave figure")
    visualization.figure_abs_condition_wave(abs_df)

    logger.info("ABS government problem-solving expectation figure (2013 only)")
    visualization.figure_abs_problem_solving_expectation(abs_df)

    logger.info("Triangulation figure: ABS trust vs. WGI Government Effectiveness")
    visualization.figure_triangulation(abs_df, panel)


def run_pipeline(raw_dir: Path, skip_mediation: bool, log_level: str) -> None:
    logger = setup_logging(level=getattr(logging, log_level))
    logger.info("Starting pipeline. Raw data dir: %s", raw_dir)

    panel, abs_df = run_preprocessing(raw_dir, logger)
    run_analysis(panel, abs_df, logger, skip_mediation=skip_mediation)
    run_visualization(panel, abs_df, logger)

    logger.info("Pipeline complete. Panel -> %s | Figures -> %s", config.PANEL_CSV, config.FIGURES_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=config.DATA_RAW_DIR,
        help="Directory containing the manually-downloaded WGI/V-Dem/ABS files.",
    )
    parser.add_argument(
        "--skip-mediation", action="store_true", help="Skip the CFA/bootstrap mediation models (slowest step)."
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    run_pipeline(args.raw_dir, args.skip_mediation, args.log_level)


if __name__ == "__main__":
    main()
