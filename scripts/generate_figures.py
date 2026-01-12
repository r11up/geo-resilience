#!/usr/bin/env python
"""Figure-generation step only: load already-processed data from
``data/processed/`` and regenerate every named figure under ``figures/``.

Useful for iterating on plot styling without re-running the slow raw-data
fetch or the mediation models. Requires ``scripts/preprocess.py`` (or the
full ``scripts/run_pipeline.py``) to have been run at least once already.

Usage
-----
    python scripts/generate_figures.py
    python scripts/generate_figures.py --log-level DEBUG
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_pipeline import run_visualization
from src import config
from src.utils import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logger = setup_logging(level=getattr(logging, args.log_level))

    for path in (config.PANEL_CSV, config.ABS_CSV):
        if not path.exists():
            raise FileNotFoundError(
                f"Processed file not found: {path}\n\n"
                "Run scripts/preprocess.py (or scripts/run_pipeline.py) first "
                "to produce data/processed/ outputs."
            )

    logger.info("Loading processed panel -> %s", config.PANEL_CSV)
    panel = pd.read_csv(config.PANEL_CSV)
    logger.info("Loading processed ABS data -> %s", config.ABS_CSV)
    abs_df = pd.read_csv(config.ABS_CSV)

    run_visualization(panel, abs_df, logger)
    logger.info("Figure generation complete. Figures -> %s", config.FIGURES_DIR)


if __name__ == "__main__":
    main()
