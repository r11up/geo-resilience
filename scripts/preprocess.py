#!/usr/bin/env python
"""Data-preparation step only: load raw data -> build panel + ABS frame ->
save to ``data/processed/``.

Useful for iterating on preprocessing without re-running the (slower)
analysis and figure-generation steps. See ``scripts/run_pipeline.py`` for
the full end-to-end pipeline.

Usage
-----
    python scripts/preprocess.py
    python scripts/preprocess.py --raw-dir /path/to/raw --log-level DEBUG
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_pipeline import run_preprocessing
from src import config
from src.utils import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=config.DATA_RAW_DIR,
        help="Directory containing the manually-downloaded WGI/V-Dem/ABS files.",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logger = setup_logging(level=getattr(logging, args.log_level))
    logger.info("Starting preprocessing only. Raw data dir: %s", args.raw_dir)
    panel, abs_df = run_preprocessing(args.raw_dir, logger)
    logger.info(
        "Preprocessing complete. Panel -> %s (%s) | ABS -> %s (%s)",
        config.PANEL_CSV,
        panel.shape,
        config.ABS_CSV,
        abs_df.shape,
    )


if __name__ == "__main__":
    main()
