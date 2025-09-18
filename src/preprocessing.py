"""Data acquisition and harmonization.

Ports Sections 4, 4b, 5b, 6, 7, 8, and 21d/21f of ``nepal_south_asia_timeseries_V7.ipynb``
unchanged: World Bank WDI fetching (API), the manual WGI file loader, the manual
V-Dem file loader, master-panel construction, and Asian Barometer (ABS) wave
loading/recoding. No formulas, filters, or thresholds were altered from the notebook.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import requests

from src import config

logger = logging.getLogger("nepal_south_asia")

WB_BASE = "https://api.worldbank.org/v2"


# --------------------------------------------------------------------------
# World Bank WDI (classic v2 API) -- migration, remittances, socio-economic
# --------------------------------------------------------------------------
def _wb_url(
    countries: Iterable[str],
    indicators: Iterable[str],
    start_year: int,
    end_year: int,
    page: int = 1,
    per_page: int = 20000,
) -> str:
    c = ";".join(countries)
    i = ";".join(indicators)
    return (
        f"{WB_BASE}/country/{c}/indicator/{i}"
        f"?format=json&date={start_year}:{end_year}&per_page={per_page}&page={page}"
    )


def _parse_wb_json(payload) -> tuple[pd.DataFrame, dict]:
    if isinstance(payload, dict):  # WB returns a dict (error message) instead of a list on failure
        raise RuntimeError(payload)
    if not payload or len(payload) < 2 or payload[1] is None:
        return pd.DataFrame(columns=["country", "iso3", "indicator", "year", "value"]), {"pages": 1}
    meta, records = payload[0], payload[1]
    rows = [
        {
            "country": r["country"]["value"],
            "iso3": r["countryiso3code"],
            "indicator": r["indicator"]["id"],
            "year": int(r["date"]),
            "value": r["value"],
        }
        for r in records
    ]
    return pd.DataFrame(rows), meta


def fetch_worldbank(
    countries: list[str],
    indicators: list[str],
    start_year: int,
    end_year: int,
    pause: float = 0.4,
    max_retries: int = 4,
) -> pd.DataFrame:
    """Fetch one or more WDI indicators for the given countries/years.

    Returns a tidy long frame: country, iso3, indicator, year, value.
    """
    sess = requests.Session()
    all_frames = []
    for indicator in indicators:
        page = 1
        total_pages = 1
        while page <= total_pages:
            url = _wb_url(countries, [indicator], start_year, end_year, page=page)
            payload = None
            for attempt in range(max_retries):
                try:
                    resp = sess.get(url, timeout=30)
                    resp.raise_for_status()
                    payload = resp.json()
                    break
                except Exception:
                    time.sleep(pause * (attempt + 1))
            if payload is None:
                raise RuntimeError(f"Failed to fetch\n{url}")
            df, meta = _parse_wb_json(payload)
            all_frames.append(df)
            total_pages = int(meta.get("pages", 1))
            page += 1
            time.sleep(pause)
    out = pd.concat(all_frames, ignore_index=True)
    out = out.dropna(subset=["value"])
    return out.sort_values(["indicator", "iso3", "year"]).reset_index(drop=True)


def long_to_wide(df_long: pd.DataFrame) -> pd.DataFrame:
    """Pivot a tidy long indicator frame to one row per (iso3, year)."""
    wide = df_long.pivot_table(index=["iso3", "year"], columns="indicator", values="value").reset_index()
    wide.columns.name = None
    return wide.sort_values(["iso3", "year"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Worldwide Governance Indicators -- manually downloaded file (Section 4b)
# --------------------------------------------------------------------------
def _match_indicator(series_name) -> str | None:
    s = str(series_name).strip().lower()
    for code_, needles in config.WGI_NAME_MATCH.items():
        if any(n in s for n in needles):
            return code_
    return None


def load_wgi_manual(path: str | Path, countries: list[str] | None = None, verbose: bool = True) -> pd.DataFrame:
    """Read a manually downloaded DataBank/WGI export (CSV or Excel) and return
    the same tidy schema as :func:`fetch_worldbank`, so everything downstream
    needs zero changes regardless of where WGI came from.
    """
    if str(path).lower().endswith((".xlsx", ".xls")):
        raw = pd.read_excel(path)
    else:
        raw = pd.read_csv(path)

    if verbose:
        logger.info("Raw WGI file shape: %s", raw.shape)
        logger.info("Raw columns (first 8): %s ...", list(raw.columns)[:8])

    cols_lower = {c: str(c).strip().lower() for c in raw.columns}

    def find_col(*keywords):
        for c, cl in cols_lower.items():
            if all(k in cl for k in keywords):
                return c
        return None

    series_name_col = find_col("series", "name")
    country_name_col = find_col("country", "name")
    country_code_col = find_col("country", "code")

    missing = [
        n
        for n, c in [
            ("Series Name", series_name_col),
            ("Country Name", country_name_col),
            ("Country Code", country_code_col),
        ]
        if c is None
    ]
    if missing:
        raise ValueError(
            f"Couldn't find expected column(s) {missing}. Actual columns are: {list(raw.columns)}\n"
            "DataBank sometimes adds a couple of title rows above the real header -- if so, "
            "re-run with e.g. pd.read_csv(path, skiprows=N) adjusted."
        )

    year_cols = [c for c in raw.columns if re.match(r"^\d{4}", str(c).strip())]
    if verbose:
        if year_cols:
            logger.info("Detected %d year columns (%s ... %s)", len(year_cols), year_cols[0], year_cols[-1])
        else:
            logger.warning("No year columns detected!")

    df = raw.dropna(subset=[country_code_col]).copy()
    df = df[df[country_code_col].astype(str).str.len() == 3]

    df["indicator"] = df[series_name_col].apply(_match_indicator)
    unmatched = sorted(set(df.loc[df["indicator"].isna(), series_name_col].astype(str)))
    if unmatched and verbose:
        logger.info(
            "%d series in the file weren't one of the 6 WGI dimensions and were skipped: %s", len(unmatched), unmatched
        )
    df = df.dropna(subset=["indicator"])

    missing_dims = sorted(set(config.WGI_NAME_MATCH) - set(df["indicator"].unique()))
    if missing_dims and verbose:
        logger.warning("These WGI dimensions were NOT found in the file at all: %s", missing_dims)

    long_df = df.melt(
        id_vars=[country_name_col, country_code_col, "indicator"],
        value_vars=year_cols,
        var_name="year_raw",
        value_name="value",
    )
    long_df["year"] = long_df["year_raw"].str.extract(r"(\d{4})").astype(int)
    long_df["value"] = long_df["value"].astype(str).str.strip().replace(list(config.MISSING_MARKERS), np.nan)
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
    long_df = long_df.rename(columns={country_name_col: "country", country_code_col: "iso3"})
    long_df = long_df.dropna(subset=["value"])

    if countries:
        long_df = long_df[long_df["iso3"].isin(countries)]

    out = (
        long_df[["country", "iso3", "indicator", "year", "value"]]
        .sort_values(["indicator", "iso3", "year"])
        .reset_index(drop=True)
    )

    if verbose:
        logger.info("Parsed tidy WGI shape: %s", out.shape)
        if len(out):
            logger.info("Year range: %d-%d", out["year"].min(), out["year"].max())
    return out


# --------------------------------------------------------------------------
# V-Dem -- manually downloaded "Country-Year: V-Dem Full+Others" CSV (Section 5b)
# --------------------------------------------------------------------------
def load_vdem_manual(
    path: str | Path,
    indicator_codes: list[str],
    countries: list[str] | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Read ONLY the requested columns from the full V-Dem country-year file
    (it has 4,000+ columns; this never loads them all into memory), filter to
    the requested countries/years, and return the same tidy schema as
    :func:`fetch_worldbank` / :func:`load_wgi_manual`.
    """
    id_cols = ["country_name", "country_text_id", "year"]
    wanted = list(dict.fromkeys(id_cols + list(indicator_codes)))

    header = pd.read_csv(path, nrows=0).columns.tolist()
    present = [c for c in wanted if c in header]
    missing = [c for c in wanted if c not in header]
    if missing and verbose:
        logger.warning(
            "%d requested V-Dem column(s) not found in this file and will be skipped "
            "(check spelling / your V-Dem version): %s",
            len(missing),
            missing,
        )

    raw = pd.read_csv(path, usecols=present, low_memory=False)
    if verbose:
        logger.info(
            "Read %s rows x %d columns from the full V-Dem file (only the %d requested).",
            f"{raw.shape[0]:,}",
            raw.shape[1],
            len(present),
        )

    df = raw.copy()
    if countries:
        not_found = sorted(set(countries) - set(df["country_text_id"].unique()))
        if not_found and verbose:
            logger.warning("These requested countries were NOT found by country_text_id: %s", not_found)
        df = df[df["country_text_id"].isin(countries)]

    if start_year is not None:
        df = df[df["year"] >= start_year]
    if end_year is not None:
        df = df[df["year"] <= end_year]

    value_cols = [c for c in present if c not in id_cols]
    long_df = df.melt(id_vars=id_cols, value_vars=value_cols, var_name="indicator", value_name="value")
    long_df = long_df.rename(columns={"country_name": "country", "country_text_id": "iso3"})
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
    long_df = long_df.dropna(subset=["value"])

    out = (
        long_df[["country", "iso3", "indicator", "year", "value"]]
        .sort_values(["indicator", "iso3", "year"])
        .reset_index(drop=True)
    )

    if verbose:
        logger.info("Parsed tidy V-Dem shape: %s", out.shape)
        if len(out):
            logger.info("Year range: %d-%d", out["year"].min(), out["year"].max())
    return out


# --------------------------------------------------------------------------
# Master country-year panel (Section 7-8)
# --------------------------------------------------------------------------
def build_master_panel(
    wgi_long: pd.DataFrame, vdem_long: pd.DataFrame, migration_long: pd.DataFrame, socioecon_long: pd.DataFrame
) -> pd.DataFrame:
    """Merge the four tidy long sources into one wide country-year panel,
    attach a linearly-interpolated migrant-stock column for trend plotting,
    and return it.
    """
    long_all = pd.concat([wgi_long, vdem_long, migration_long, socioecon_long], ignore_index=True)
    panel = long_to_wide(long_all)
    panel["country"] = panel["iso3"].map(config.COUNTRY_NAMES)

    # SM.POP.TOTL_filled: a linearly-interpolated version of the 5-year migrant-
    # stock series, for TREND PLOTTING ONLY (Figure B). Interior gaps (between two
    # known 5-year checkpoints) are filled with a straight line between them; the
    # leading/trailing edges hold the nearest known value flat. Stored as a
    # SEPARATE column -- never use it in a correlation/Granger cell, where the
    # interpolation would fabricate autocorrelation not present in the real data.
    if "SM.POP.TOTL" in panel.columns:
        panel["SM.POP.TOTL_filled"] = panel.groupby("iso3")["SM.POP.TOTL"].transform(
            lambda s: s.interpolate(method="linear", limit_direction="both")
        )
    return panel


def panel_missingness_report(panel: pd.DataFrame) -> pd.DataFrame:
    """Percent-missing by country x indicator (0 = fully observed)."""
    return panel.set_index(["country", "year"]).drop(columns=["iso3"]).isna().groupby(level=0).mean().round(2) * 100


# --------------------------------------------------------------------------
# Asian Barometer (ABS) -- text-response recoding and wave loading (Section 21d/21f)
# --------------------------------------------------------------------------
def _strip_leading_code(text):
    if not isinstance(text, str):
        return text
    m = re.match(r"^\s*-?\d+\s*:\s*(.*)$", text)
    return m.group(1).strip() if m else text.strip()


def _is_missing(stripped_text) -> bool:
    if stripped_text is None:
        return True
    t = str(stripped_text).strip().lower()
    if t in ("-1", "nan", ""):
        return True
    return any(p in t for p in config.MISSING_SUBSTRINGS)


def recode_scale(series: pd.Series, mapping: dict[str, float], name: str = "", verbose: bool = True) -> pd.Series:
    """Recode a raw ABS text-response column onto a numeric ordinal scale.

    ``mapping``: {lowercase substring: ordinal value}, matched longest-pattern-first.
    Unmatched non-missing text -> NaN, with a printed warning.
    """
    patterns = sorted(mapping.items(), key=lambda kv: -len(kv[0]))
    out, unmatched = [], set()
    for raw in series:
        stripped = _strip_leading_code(raw)
        if _is_missing(stripped):
            out.append(np.nan)
            continue
        low = str(stripped).strip().lower()
        hit = None
        for pat, val in patterns:
            if pat in low:
                hit = val
                break
        if hit is None:
            unmatched.add(stripped)
            out.append(np.nan)
        else:
            out.append(hit)
    if unmatched and verbose:
        logger.info("(%s) %d unmapped value(s) -> coded missing: %s", name, len(unmatched), sorted(unmatched))
    return pd.Series(out, index=series.index, dtype=float)


def load_abs_wave(
    path: str | Path,
    wave_label: str,
    year: int,
    country_col: str,
    trust_items: list[str],
    condition_items: dict[str, dict[str, float]],
    regime_pref_col: str,
    satisfaction_col: str,
    extra_item_col: str | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Load one ABS wave (.xlsx), recode every item this study uses onto a
    common numeric scale, and return one row per respondent.
    """
    raw = pd.read_excel(path)
    if verbose:
        logger.info("[%s] loaded %s rows x %d columns from %s", wave_label, f"{raw.shape[0]:,}", raw.shape[1], path)

    expected = [country_col, regime_pref_col, satisfaction_col] + trust_items + list(condition_items)
    missing_cols = [c for c in expected if c not in raw.columns]
    if missing_cols and verbose:
        logger.warning("[%s] expected column(s) not in this file, skipped: %s", wave_label, missing_cols)

    out = pd.DataFrame(index=raw.index)
    out["country"] = raw[country_col].apply(_strip_leading_code) if country_col in raw.columns else np.nan
    out["wave"] = wave_label
    out["year"] = year

    present_trust = [c for c in trust_items if c in raw.columns]
    for i, c in enumerate(present_trust):
        out[f"trust_item_{i}"] = recode_scale(raw[c], config.TRUST_SCALE, name=f"{wave_label}:{c}", verbose=verbose)
    trust_cols = [f"trust_item_{i}" for i in range(len(present_trust))]
    out["trust_composite"] = out[trust_cols].mean(axis=1, skipna=True) if trust_cols else np.nan
    out["n_trust_items_answered"] = out[trust_cols].notna().sum(axis=1) if trust_cols else 0

    cond_cols = []
    for c, scale in condition_items.items():
        if c in raw.columns:
            colname = f"_cond_{c}"
            out[colname] = recode_scale(raw[c], scale, name=f"{wave_label}:{c}", verbose=verbose)
            cond_cols.append(colname)
    if cond_cols:
        z = out[cond_cols].apply(lambda s: (s - s.mean()) / s.std(ddof=1) if s.std(ddof=1) else s * 0)
        out["condition_composite"] = z.mean(axis=1, skipna=True)
    else:
        out["condition_composite"] = np.nan

    if regime_pref_col in raw.columns:
        out["regime_preference"] = recode_scale(
            raw[regime_pref_col], config.REGIME_PREF_SCALE, name=f"{wave_label}:{regime_pref_col}", verbose=verbose
        )
    if satisfaction_col in raw.columns:
        out["satisfaction_democracy"] = recode_scale(
            raw[satisfaction_col], config.SATISFACTION_SCALE, name=f"{wave_label}:{satisfaction_col}", verbose=verbose
        )
    if extra_item_col and extra_item_col in raw.columns:
        out["extra_item_raw"] = recode_scale(
            raw[extra_item_col], config.LIKELY_SCALE, name=f"{wave_label}:{extra_item_col}", verbose=verbose
        )

    if verbose:
        logger.info("[%s] countries: %s", wave_label, sorted(out["country"].dropna().unique()))
        logger.info(
            "[%s] trust_composite: mean=%.2f (n valid=%d/%d)",
            wave_label,
            out["trust_composite"].mean(),
            out["trust_composite"].notna().sum(),
            len(out),
        )
    return out


def load_abs_waves(wave1_path: str | Path | None, wave2_path: str | Path | None, verbose: bool = True) -> pd.DataFrame:
    """Load and concatenate ABS Wave 1 (2005) and Wave 2 (2013), whichever are provided."""
    w1_df = (
        load_abs_wave(
            wave1_path,
            "2005",
            2005,
            config.WAVE1_COUNTRY_COL,
            config.WAVE1_TRUST_ITEMS,
            config.WAVE1_CONDITION_ITEMS,
            config.WAVE1_REGIME_PREF_COL,
            config.WAVE1_SATISFACTION_DEMOCRACY_COL,
            config.WAVE1_PROBLEM_SOLVING_EXPECTATION_COL,
            verbose=verbose,
        )
        if wave1_path
        else None
    )
    w2_df = (
        load_abs_wave(
            wave2_path,
            "2013",
            2013,
            config.WAVE2_COUNTRY_COL,
            config.WAVE2_TRUST_ITEMS,
            config.WAVE2_CONDITION_ITEMS,
            config.WAVE2_REGIME_PREF_COL,
            config.WAVE2_SATISFACTION_DEMOCRACY_COL,
            config.WAVE2_PROBLEM_SOLVING_EXPECTATION_COL,
            verbose=verbose,
        )
        if wave2_path
        else None
    )
    frames = [d for d in (w1_df, w2_df) if d is not None]
    if not frames:
        raise ValueError("Neither wave1_path nor wave2_path was provided.")
    return pd.concat(frames, ignore_index=True)
