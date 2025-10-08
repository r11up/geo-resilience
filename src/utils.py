"""Small, generic helpers shared across modules: label lookups, logging setup,
and filesystem convenience functions.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src import config


def label_for(code: str, short: bool = False) -> str:
    """Human-readable name for any indicator code used in this project.

    Falls back to the raw code only if it truly isn't registered anywhere.
    """
    if short and code in config.SHORT_LABELS:
        return config.SHORT_LABELS[code]
    return config.INDICATOR_LABELS.get(code, config.SHORT_LABELS.get(code, code))


def country_name(iso3: str) -> str:
    """Full country name for an ISO3 code, falling back to the code itself."""
    return config.COUNTRY_NAMES.get(iso3, iso3)


def ensure_dir(path: Path) -> Path:
    """Create ``path`` (and parents) if missing, and return it unchanged."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure a project-wide console logger and return it.

    Safe to call multiple times (e.g. once per script) -- handlers are not
    duplicated on repeat calls.
    """
    logger = logging.getLogger("nepal_south_asia")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
