#!/usr/bin/env python
"""Paper-reproduction entry point.

Thin wrapper around ``scripts/run_pipeline.py`` -- this is the single
command referenced in the README's "How to Reproduce the Paper" section.
It runs the full pipeline (preprocess -> analyze -> generate figures) with
the same CLI options as ``run_pipeline.py``.

Usage
-----
    python scripts/reproduce_results.py
    python scripts/reproduce_results.py --raw-dir /path/to/raw --skip-mediation
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_pipeline import main

if __name__ == "__main__":
    main()
