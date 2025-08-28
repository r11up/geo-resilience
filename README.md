# Nepal & South Asia Timeseries: Public Trust and Geo Spatial Resilience

Reproducible data pipeline and figure generator for the paper **"Public Trust and Geo Spatial
Resilience"** (Poudel, 2026). This repository contains the full country-year panel
construction, statistical analysis, and figure generation code underlying the paper, refactored
from the original research notebook into a modular, tested, documented Python package.

## Overview

The paper asks why, despite two decades of relatively stable macro-governance indicators, young
Nepalis continue to leave the country in large numbers. It builds a country-year panel for Nepal
and five South Asian comparators (India, Bangladesh, Pakistan, Sri Lanka, Bhutan) spanning
expert-coded governance indices (WGI, V-Dem), migration and remittance flows (World Bank WDI),
and socio-economic indicators, and pairs it with individual-level survey data (Asian Barometer
Survey, 2005 and 2013 waves) on institutional trust, perceived conditions, and regime preference.

Analytically, the project:

- Screens governance-migration co-movement with **stationarity-gated Granger causality** (an
  ADF+KPSS AND-gate that suppresses spurious significance on non-stationary series), both for
  Nepal alone and pooled across all six countries (Dumitrescu–Hurlin-style panel Granger test
  with a circular-shift bootstrap p-value).
- Forecasts Nepal's remittance and government-effectiveness trajectories with three independently
  fit models (linear trend, Holt, small-grid ARIMA) and backtests each against held-out years.
- Tests a mediation model (perceived conditions → institutional trust → regime
  preference/migration-relevant outcomes) via CFA + bootstrapped indirect effects (`semopy`), run
  separately per ABS wave, for both a Nepal-only subset and the pooled 5-country sample.
- Cross-validates the individual-level ABS trust data against the country-year expert-coded
  governance panel as a convergent-validity check.

## Research motivation

Standard governance indicators (WGI, V-Dem) are expert-coded, country-year aggregates — they can
miss what individuals actually perceive and act on. This project treats the Asian Barometer
Survey's individual-level trust and perceived-condition items as an empirical proxy for the
"spatial cognition" people use when weighing whether to stay or leave (an application of
Hirschman's Exit-Voice-Loyalty framework, where V-Dem's "Freedom of Foreign Movement" indicator
is read as the literal *exit* option), and asks whether that perception-level signal tracks —
and helps explain — realized youth out-migration better than the macro indicators alone.

## Methodology

1. **Panel construction** — merge expert-coded governance (WGI, V-Dem), World Bank migration /
   remittance / socio-economic indicators, and Asian Barometer respondent-level data into a
   common country-year panel (1996–2024) and a harmonized respondent-level frame (2005, 2013).
2. **Internal QA** — cross-check the manually-downloaded WGI file against V-Dem's own bundled WGI
   estimates (these should closely agree; a low correlation flags a parsing bug, not a real
   disagreement between sources).
3. **Co-movement tests** — stationarity-gated Granger causality (single-country and pooled/panel)
   between exit-option freedom and net migration (primary) and between corruption and remittances
   (secondary robustness check).
4. **Forecasting** — linear trend, Holt exponential smoothing, and small-grid ARIMA, each
   backtested on held-out years, for Nepal's remittances (% GDP) and Government Effectiveness.
5. **Survey analysis** — Cronbach's alpha for the ABS trust-item battery, wave-over-wave
   (2005 vs. 2013) comparisons of trust/regime preference/perceived condition by country, and a
   CFA + bootstrapped mediation model linking perceived conditions → trust → downstream outcomes.
6. **Triangulation** — does individual-level ABS trust track the expert-coded governance panel
   for the same country-years? A convergent-validity check, not a substitute for either dataset.

All formulas, thresholds, random seeds, and indicator codes are ported **verbatim** from the
original research notebook (`notebooks/archive/nepal_south_asia_timeseries_V7.ipynb`) — this
refactor changes organization and reproducibility, not methodology or results.

## Repository structure

```
publicpolicy/
├── README.md                    # this file
├── LICENSE                      # MIT
├── CITATION.cff                 # citation metadata (fill in author/repo details)
├── requirements.txt             # pinned pip dependencies
├── environment.yml              # conda equivalent
├── pyproject.toml               # project metadata, black/ruff/pytest config
├── .gitignore
├── data/
│   ├── README.md                 # raw-file acquisition instructions (start here)
│   ├── raw/                      # manually-downloaded source files (gitignored)
│   └── processed/                # pipeline outputs: panel + ABS CSVs (gitignored)
├── notebooks/
│   ├── 01_data_preparation.ipynb # loads raw sources, builds & saves the panel/ABS CSVs
│   ├── 02_analysis.ipynb         # Granger, forecasting, reliability, mediation
│   ├── 03_visualization.ipynb    # generates every paper figure
│   └── archive/
│       └── nepal_south_asia_timeseries_V7.ipynb  # original, unmodified research notebook
├── src/
│   ├── config.py                 # paths, indicator dictionaries, ABS scale maps
│   ├── preprocessing.py          # raw-file loaders + master panel/ABS builders
│   ├── statistics.py             # generic statistical primitives (Granger, forecasting, alpha)
│   ├── analysis.py               # paper-specific analysis orchestration
│   ├── plotting.py                # chart primitives
│   ├── visualization.py          # one function per named paper figure
│   └── utils.py                   # logging setup, label/country-name helpers
├── scripts/
│   ├── run_pipeline.py            # canonical end-to-end pipeline (preprocess+analyze+plot)
│   ├── preprocess.py               # preprocessing only
│   ├── generate_figures.py         # figures only, from already-processed CSVs
│   └── reproduce_results.py        # alias for run_pipeline.py
├── figures/                        # generated PNG+PDF figures (gitignored)
├── outputs/                        # reserved for tabular/numeric result exports (gitignored)
├── docs/                            # supplementary documentation
└── tests/
    └── test_basic.py                # smoke tests + 2 deterministic self-checks
```

## Installation

Requires Python ≥3.10.

**pip**
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**conda**
```bash
conda env create -f environment.yml
conda activate nepal-south-asia-timeseries
```

## Requirements

Core: `pandas`, `numpy`, `scipy`, `statsmodels`, `matplotlib`, `semopy`, `requests`, `openpyxl`.
Notebooks: `jupyter`, `ipykernel`, `nbformat`, `nbconvert`. Testing: `pytest`. See
[requirements.txt](requirements.txt) for exact pinned versions.

## Quick start

1. Download the four manually-sourced raw files (WGI, V-Dem, ABS waves 1 & 2) into `data/raw/` —
   see [data/README.md](data/README.md) for exact download links and filenames. (Migration and
   socio-economic indicators are fetched automatically from the World Bank API; no download
   needed for those.)
2. Run the full pipeline:
   ```bash
   python scripts/run_pipeline.py
   ```
   This loads and merges all raw sources, runs every analysis (Granger, forecasting, ABS
   reliability, mediation), and writes every figure to `figures/`.

### Example commands

```bash
# Full pipeline, default settings
python scripts/run_pipeline.py

# Full pipeline, skip the slowest step (CFA/bootstrap mediation models)
python scripts/run_pipeline.py --skip-mediation

# Raw files somewhere other than data/raw/
python scripts/run_pipeline.py --raw-dir /path/to/raw

# Just rebuild data/processed/ from data/raw/, no analysis or figures
python scripts/preprocess.py

# Just regenerate figures from an existing data/processed/ (skip re-downloading/reprocessing)
python scripts/generate_figures.py

# Verbose logging
python scripts/run_pipeline.py --log-level DEBUG
```

`scripts/reproduce_results.py` is an alias for `scripts/run_pipeline.py`, provided for
readers looking for a "reproduce the paper" entry point by that name.

## Expected outputs

- `data/processed/south_asia_panel.csv` — country-year panel, all 6 countries, 1996–2024.
- `data/processed/abs_respondent_level.csv` — harmonized Asian Barometer respondent-level data,
  both waves.
- `figures/*.png` and `figures/*.pdf` — every paper figure, saved in both formats. See the
  figure↔paper-section map below.
- Console/log output for every analysis step (QA crosscheck correlations, Granger test p-values,
  forecast R²/backtest metrics, Cronbach's alpha, mediation indirect-effect estimates and
  bootstrap confidence intervals).

## Figure ↔ paper-section map

| Figure | Function (`src/visualization.py`) | Content |
|---|---|---|
| A | `figure_a_governance_trends` | WGI governance/trust trends, Nepal vs. South Asia |
| A2 | `figure_a2_vdem_trends` | V-Dem governance & civic-space trends |
| B | `figure_b_migration_trends` | Migration/remittance trends |
| C | `figure_c_socioeconomic_trends` | GDP/capita, enrollment, youth unemployment |
| D | `figure_d_correlation_heatmap` | Nepal exit/governance/migration-proxy co-movement heatmap |
| E | `figure_e_remittances_forecast` | Nepal remittances (% GDP): observed + 3 forecasts + backtest |
| F | `figure_f_governance_forecast` | Nepal Government Effectiveness: observed + 3 forecasts + backtest |
| G | `figure_g_democratic_resilience` | Democratic Resilience (V-Dem Regimes of the World) |
| ABS trust wave | `figure_abs_trust_wave` | Institutional trust by country, 2005 vs. 2013 |
| ABS trust by institution | `figure_abs_trust_by_institution` | Institution-level trust breakdown, per wave |
| ABS regime wave | `figure_abs_regime_wave` | Regime preference (pro-democracy attitude) by country |
| ABS condition wave | `figure_abs_condition_wave` | Perceived economic/national condition by country |
| ABS problem-solving | `figure_abs_problem_solving_expectation` | Government problem-solving expectation, 2013 only |
| Triangulation | `figure_triangulation` | ABS aggregate trust vs. expert-coded WGI Government Effectiveness |
| Mediation | `analysis.run_mediation_for_subset` (called from `run_pipeline.py`) | CFA + bootstrapped mediation, per wave, per outcome, per subset |

Each `src/visualization.py` function docstring also names the exact original notebook section it
ports. See `notebooks/archive/nepal_south_asia_timeseries_V7.ipynb` for the original, unmodified
research notebook.

## How to reproduce the paper

1. Follow [data/README.md](data/README.md) to obtain the four raw files.
2. Run `python scripts/run_pipeline.py` (or the cleaned notebooks `notebooks/01_data_preparation.ipynb`
   → `02_analysis.ipynb` → `03_visualization.ipynb`, in order, if you prefer a notebook workflow).
3. All figures land in `figures/`; the processed panel and ABS CSVs land in `data/processed/`.
4. The number to quote for the remittance/governance forecasts is the **linear-trend R² (historical
   fit quality)**, not the 2029 forecast endpoint — see `analysis.forecast_series_with_backtest`.

Run `pytest tests/` to verify the statistical machinery (including two deterministic self-checks
ported from the notebook's own validation cells) before trusting results on new data.

## Citation

If you use this software or its outputs, please cite both the paper and this repository — see
[CITATION.cff](CITATION.cff).

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Built on the Worldwide Governance Indicators (World Bank), the V-Dem dataset (V-Dem Institute),
World Development Indicators (World Bank), and the Asian Barometer Survey (Asian Barometer
Project). See [data/README.md](data/README.md) for full source details and access instructions.
