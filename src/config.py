"""Central configuration: paths, countries, indicator dictionaries, plotting
constants, and Asian Barometer (ABS) column/scale maps.

All values here are extracted verbatim from ``nepal_south_asia_timeseries_V7.ipynb``
(Sections 2-3, 11, 21e) with no change to indicator codes, scales, or labels.
Downstream modules import from this file instead of redefining these constants,
so there is exactly one place to update if a data source or paper mapping changes.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
# Repository root is two levels up from this file (src/config.py -> repo/).
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

DATA_DIR: Path = PROJECT_ROOT / "data"
DATA_RAW_DIR: Path = DATA_DIR / "raw"
DATA_PROCESSED_DIR: Path = DATA_DIR / "processed"

FIGURES_DIR: Path = PROJECT_ROOT / "figures"
OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"

PANEL_CSV: Path = DATA_PROCESSED_DIR / "south_asia_panel.csv"
ABS_CSV: Path = DATA_PROCESSED_DIR / "abs_respondent_level.csv"

# Manually-downloaded source files (see data/README.md for acquisition steps).
# These live in data/raw/ and are NOT committed to version control.
WGI_RAW_PATH: Path = DATA_RAW_DIR / "wgi_export.xlsx"
VDEM_RAW_PATH: Path = DATA_RAW_DIR / "V-Dem-CY-Full+Others.csv"
ABS_WAVE1_RAW_PATH: Path = DATA_RAW_DIR / "wave1_2005.xlsx"
ABS_WAVE2_RAW_PATH: Path = DATA_RAW_DIR / "wave2_2013.xlsx"

# --------------------------------------------------------------------------
# Countries (Section 3)
# --------------------------------------------------------------------------
COUNTRIES: list[str] = ["NPL", "IND", "BGD", "PAK", "LKA", "BTN"]
FOCAL: str = "NPL"
COUNTRY_NAMES: dict[str, str] = {
    "NPL": "Nepal",
    "IND": "India",
    "BGD": "Bangladesh",
    "PAK": "Pakistan",
    "LKA": "Sri Lanka",
    "BTN": "Bhutan",
}

# --------------------------------------------------------------------------
# Category 1 & 4 -- Worldwide Governance Indicators (manual file load)
# --------------------------------------------------------------------------
WGI_INDICATORS: dict[str, str] = {
    "GOV_WGI_VA": "Voice & Accountability",
    "GOV_WGI_PV": "Political Stability & Absence of Violence",
    "GOV_WGI_GE": "Government Effectiveness",
    "GOV_WGI_RQ": "Regulatory Quality",
    "GOV_WGI_RL": "Rule of Law",
    "GOV_WGI_CC": "Control of Corruption",
}

# Matched by NAME inside preprocessing.load_wgi_manual(); keys are internal labels.
WGI_NAME_MATCH: dict[str, list[str]] = {
    "GOV_WGI_VA": ["voice and account"],
    "GOV_WGI_PV": ["political stability"],
    "GOV_WGI_GE": ["government effectiveness"],
    "GOV_WGI_RQ": ["regulatory quality"],
    "GOV_WGI_RL": ["rule of law"],
    "GOV_WGI_CC": ["control of corruption"],
}
MISSING_MARKERS: set[str] = {"..", "", "na", "n/a", "#n/a", "..."}

# --------------------------------------------------------------------------
# V-Dem indicators, trimmed in V7 to groups with a nameable tie to the paper
# --------------------------------------------------------------------------
VDEM_DEMOCRACY_INDICATORS: dict[str, str] = {
    "v2x_polyarchy": "Electoral democracy index (V-Dem)",
    "v2x_libdem": "Liberal democracy index (V-Dem)",
    "v2x_civlib": "Civil liberties index (V-Dem)",
    "v2xcs_ccsi": "Core civil society index (V-Dem)",
}
# The paper's own stated operationalization of "democratic resilience"
# (Fig. 2's terminal node) -- given its own dedicated figure (Figure G).
VDEM_RESILIENCE_OUTCOME_INDICATORS: dict[str, str] = {
    "v2x_regime": ("Democratic Resilience -- Regimes of the World, " "0=Closed Autocracy..3=Liberal Democracy (V-Dem)"),
}
# Trimmed from 3 to 1 in V7: overall corruption only.
VDEM_CORRUPTION_INDICATORS: dict[str, str] = {
    "v2x_corr": "Political Corruption Index, overall (V-Dem)",
}
# v2clfmove is "the literal exit option" in Hirschman's Exit-Voice-Loyalty framework.
VDEM_VOICE_EXIT_INDICATORS: dict[str, str] = {
    "v2clfmove": "Freedom of Foreign Movement (V-Dem) -- the 'exit' option in Hirschman's EVL framework",
    "v2x_freexp_altinf": "Freedom of Expression & Alternative Information (V-Dem)",
    "v2x_frassoc_thick": "Freedom of Association, thick (V-Dem)",
}
# Trimmed from 3 to 1 in V7: administrative reach only.
VDEM_STATECAPACITY_INDICATORS: dict[str, str] = {
    "v2strenadm": "State Administrative Capacity / Reach (V-Dem)",
}
# Speaks directly to the Sept. 2025 social-media-ban episode (Section 5.6/5.7).
VDEM_SOCIALMEDIA_INDICATORS: dict[str, str] = {
    "v2smgovshutcap": "Government Social Media Shutdown Capacity (V-Dem)",
    "v2smgovshut": "Government Social Media Shutdown in Practice (V-Dem)",
    "v2smgovfilcap": "Government Internet Filtering Capacity (V-Dem)",
    "v2smregcap": "Government Social Media Regulation Capacity (V-Dem)",
}
# Internal QA only (Section 7b): confirms the manually-downloaded WGI file
# parsed correctly, by comparing it to V-Dem's own bundled WGI estimates.
VDEM_WGI_CROSSCHECK_INDICATORS: dict[str, str] = {
    "e_wbgi_gee": "Government Effectiveness, WGI (bundled in V-Dem, QA only)",
    "e_wbgi_cce": "Control of Corruption, WGI (bundled in V-Dem, QA only)",
    "e_wbgi_rqe": "Regulatory Quality, WGI (bundled in V-Dem, QA only)",
    "e_wbgi_rle": "Rule of Law, WGI (bundled in V-Dem, QA only)",
    "e_wbgi_vae": "Voice & Accountability, WGI (bundled in V-Dem, QA only)",
    "e_wbgi_pve": "Political Stability & Absence of Violence, WGI (bundled in V-Dem, QA only)",
}
# Mapping used by the internal WGI-vs-V-Dem QA cross-check (Section 7b).
WGI_VS_VDEM_MAP: dict[str, str] = {
    "GOV_WGI_GE": "e_wbgi_gee",
    "GOV_WGI_CC": "e_wbgi_cce",
    "GOV_WGI_RQ": "e_wbgi_rqe",
    "GOV_WGI_RL": "e_wbgi_rle",
    "GOV_WGI_VA": "e_wbgi_vae",
    "GOV_WGI_PV": "e_wbgi_pve",
}

VDEM_INDICATORS: dict[str, str] = {
    **VDEM_DEMOCRACY_INDICATORS,
    **VDEM_RESILIENCE_OUTCOME_INDICATORS,
    **VDEM_CORRUPTION_INDICATORS,
    **VDEM_VOICE_EXIT_INDICATORS,
    **VDEM_STATECAPACITY_INDICATORS,
    **VDEM_SOCIALMEDIA_INDICATORS,
    **VDEM_WGI_CROSSCHECK_INDICATORS,
}

# --------------------------------------------------------------------------
# Category 2 -- migration / remittances (World Bank WDI, classic v2 API)
# --------------------------------------------------------------------------
MIGRATION_INDICATORS: dict[str, str] = {
    "BX.TRF.PWKR.CD.DT": "Personal Remittances Received (current US$)",
    "BX.TRF.PWKR.DT.GD.ZS": "Personal Remittances Received (% of GDP)",
    "SM.POP.NETM": "Net Migration (5-year UN DESA estimate)",
    "SM.POP.TOTL": "International Migrant Stock, Total (UN DESA)",
}
# Indicators whose raw values need billions/millions-style axis formatting.
BIG_NUMBER_INDICATORS: set[str] = {"BX.TRF.PWKR.CD.DT", "SM.POP.NETM", "SM.POP.TOTL"}

# --------------------------------------------------------------------------
# Category 3 -- socio-economic (World Bank WDI, classic v2 API)
# --------------------------------------------------------------------------
SOCIOECON_INDICATORS: dict[str, str] = {
    "NY.GDP.PCAP.CD": "GDP per Capita (current US$)",
    "SE.SEC.NENR": "Secondary School Enrollment, Net (%)",
    "SL.UEM.1524.ZS": "Youth Unemployment, Ages 15-24 (% of labor force, ILO modelled)",
}

WDI_START: int = 1990
WDI_END: int = 2024

INDICATOR_LABELS: dict[str, str] = {
    **WGI_INDICATORS,
    **VDEM_INDICATORS,
    **MIGRATION_INDICATORS,
    **SOCIOECON_INDICATORS,
}

# Short, compact display variants for space-constrained figure elements
# (heatmap tick labels, in-legend text). Everywhere else, INDICATOR_LABELS is
# the canonical name for titles, axis labels, and paper text.
SHORT_LABELS: dict[str, str] = {
    "GOV_WGI_VA": "Voice & Accountability",
    "GOV_WGI_PV": "Political Stability",
    "GOV_WGI_GE": "Government Effectiveness",
    "GOV_WGI_RQ": "Regulatory Quality",
    "GOV_WGI_RL": "Rule of Law",
    "GOV_WGI_CC": "Control of Corruption",
    "v2clfmove": "Freedom of Movement (exit)",
    "v2x_regime": "Democratic Resilience",
    "v2x_corr": "Political Corruption (V-Dem)",
    "v2x_libdem": "Liberal Democracy (V-Dem)",
    "BX.TRF.PWKR.CD.DT": "Remittances (US$)",
    "BX.TRF.PWKR.DT.GD.ZS": "Remittances (% GDP)",
    "SM.POP.NETM": "Net Migration",
    "SM.POP.TOTL": "Migrant Stock",
}

# --------------------------------------------------------------------------
# Plotting constants (Section 11)
# --------------------------------------------------------------------------
COUNTRY_COLORS: dict[str, str] = {
    "NPL": "#B23A48",  # Nepal -- kept as the accent color, still visually emphasized
    "IND": "#2A6F77",
    "BGD": "#C98A2C",
    "PAK": "#5B6EE1",
    "LKA": "#4F9D69",
    "BTN": "#8B5FBF",
}
GRID_COLOR: str = "#E3E6E8"

REGIME_CATEGORY_LABELS: dict[int, str] = {
    0: "Closed\nautocracy",
    1: "Electoral\nautocracy",
    2: "Electoral\ndemocracy",
    3: "Liberal\ndemocracy",
}

# Muted past (2005) vs. accent present (2013) for ABS wave-comparison figures.
WAVE_COLORS: dict[str, str] = {"2005": "#9AA5B1", "2013": "#B23A48"}

OUTCOME_DISPLAY: dict[str, str] = {
    "regime_preference": "Regime Preference\n(Pro-Democracy Attitude)",
    "satisfaction_democracy": "Satisfaction with\nDemocracy",
}

# --------------------------------------------------------------------------
# Asian Barometer (ABS) recoding scales (Section 21d) -- text pattern -> ordinal
# --------------------------------------------------------------------------
TRUST_SCALE: dict[str, float] = {
    "great deal": 4,
    "quite a lot": 3,
    "some": 3,
    "not very much": 2,
    "not at all": 1,
    "none at all": 1,
}
AGREE_SCALE: dict[str, float] = {
    "strongly disagree": 1,
    "strongly agree": 4,
    "disagree": 2,
    "agree": 3,
}
APPROVE_SCALE: dict[str, float] = {
    "strongly disapprove": 1,
    "strongly approve": 4,
    "disapprove": 2,
    "approve": 3,
}
CONDITION_LEVEL_SCALE: dict[str, float] = {
    "very bad": 1,
    "bad": 2,
    "so so": 3,
    "good": 4,
    "very good": 5,
}
CHANGE_SCALE: dict[str, float] = {
    "much worse": 1,
    "a little worse": 2,
    "worse": 2,
    "same": 3,
    "about the same": 3,
    "a little better": 4,
    "better": 4,
    "much better": 5,
}
SATISFACTION_SCALE: dict[str, float] = {
    "not at all satisfied": 1,
    "not very satisfied": 2,
    "somewhat satisfied": 3,
    "fairly satisfied": 3,
    "very satisfied": 4,
    "satisfied": 3,
    "neither satisfied nor dissatisfied": 2.5,
}
LIKELY_SCALE: dict[str, float] = {
    "not at all likely": 1,
    "not very likely": 2,
    "likely": 3,
    "very likely": 4,
}
REGIME_PREF_SCALE: dict[str, float] = {
    "dictatorship is preferable": 1,
    "authoritarian government can": 1,
    "does not matter": 2,
    "doesn't matter": 2,
    "democracy is preferable": 3,
    "democracy is always preferable": 3,
}
MISSING_SUBSTRINGS: list[str] = [
    "d.k",
    "don't know",
    "can't say",
    "no opinion",
    "n.a.",
    "no response",
    "not asked",
    "refused",
    "missing",
]

# --------------------------------------------------------------------------
# ABS column-role maps, Wave 1 (2005) and Wave 2 (2013) -- confirmed against
# the actual ABS questionnaires (Section 21e).
# --------------------------------------------------------------------------
WAVE1_COUNTRY_COL = "v1"
WAVE1_TRUST_ITEMS: list[str] = ["c13a", "c13c", "c13d", "c13e", "c13f", "c13g", "c13h", "c13i", "c13j"]
WAVE1_TRUST_LABELS: dict[str, str] = {
    "c13a": "Central/National government",
    "c13c": "Local government",
    "c13d": "Civil service",
    "c13e": "Police",
    "c13f": "Army",
    "c13g": "Courts",
    "c13h": "Parliament",
    "c13i": "Political parties",
    "c13j": "Election Commission",
}
WAVE1_CONDITION_ITEMS: dict[str, dict[str, float]] = {
    "b2": SATISFACTION_SCALE,
    "b7": SATISFACTION_SCALE,
    "b3": CHANGE_SCALE,
    "b4": CHANGE_SCALE,
    "b8": CHANGE_SCALE,
    "b9": CHANGE_SCALE,
}
WAVE1_REGIME_PREF_COL = "c23"
WAVE1_SATISFACTION_DEMOCRACY_COL = "c12"
WAVE1_PROBLEM_SOLVING_EXPECTATION_COL = None  # no Wave 1 equivalent of Wave 2's GBC32

WAVE2_COUNTRY_COL = "ccode"
WAVE2_TRUST_ITEMS: list[str] = [
    "GB7a",
    "GB7b",
    "GB7c",
    "GB7e",
    "GB7f",
    "GB7g",
    "GB7h",
    "GB7i",
    "GB7j",
    "GB7k",
    "GB7l",
    "GB7m",
]
WAVE2_TRUST_LABELS: dict[str, str] = {
    "GB7a": "President",
    "GB7b": "Prime Minister",
    "GB7c": "National government (capital)",
    "GB7e": "Parliament",
    "GB7f": "Local government",
    "GB7g": "Courts",
    "GB7h": "Civil service",
    "GB7i": "Political parties",
    "GB7j": "Military/armed forces",
    "GB7k": "Police",
    "GB7l": "Newspapers",
    "GB7m": "Television",
}
WAVE2_CONDITION_ITEMS: dict[str, dict[str, float]] = {
    "GB1": CONDITION_LEVEL_SCALE,
    "GBC4": CONDITION_LEVEL_SCALE,
    "GB2": CHANGE_SCALE,
    "GB3": CHANGE_SCALE,
    "GBC5": CHANGE_SCALE,
    "GBC6": CHANGE_SCALE,
}
WAVE2_REGIME_PREF_COL = "GBC34"
WAVE2_SATISFACTION_DEMOCRACY_COL = "GBC26"
WAVE2_PROBLEM_SOLVING_EXPECTATION_COL = "GBC32"

# Country order used consistently across ABS wave-comparison figures
# (5 of 6 study countries -- Bhutan is not covered by ABS).
ABS_COUNTRY_ORDER: list[str] = ["Nepal", "India", "Bangladesh", "Sri Lanka", "Pakistan"]
