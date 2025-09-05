# Data

This project uses four manually-downloaded raw source files plus two World-Bank-API
pulls that happen automatically. None of the raw files are committed to version
control (see `.gitignore`) — you must download them yourself before running the
pipeline, following the steps below. This mirrors exactly how
`notebooks/archive/nepal_south_asia_timeseries_V7.ipynb` (the original research
notebook) sourced its data; nothing about *what* is loaded or *how* it's parsed has
changed, only where the download instructions live.

## `data/raw/` — manually downloaded files

Download each file below and save it under `data/raw/` with **exactly** the filename
shown (the pipeline looks for these names; see `src/config.py` if you'd rather point
it at different paths/filenames instead of renaming your downloads).

| # | File | Save as | Source |
|---|---|---|---|
| 1 | Worldwide Governance Indicators (WGI) | `data/raw/wgi_export.xlsx` | [DataBank](https://databank.worldbank.org/source/worldwide-governance-indicators) — tick countries Nepal, India, Bangladesh, Pakistan, Sri Lanka, Bhutan; tick the six `...: Estimate` series; select all years; **Download > Excel/CSV**. Or the one-click full dataset: [wgidataset.xlsx](https://info.worldbank.org/governance/wgi/Home/downLoadFile?fileName=wgidataset.xlsx). |
| 2 | V-Dem Country-Year (Full+Others) | `data/raw/V-Dem-CY-Full+Others.csv` | [v-dem.net/data/the-v-dem-dataset](https://v-dem.net/data/the-v-dem-dataset/) — free, no login/registration. Download the full **"Country-Year: V-Dem Full+Others"** CSV; `src/preprocessing.load_vdem_manual` reads only the ~20 columns it needs, so the multi-thousand-column file does not need to be trimmed by hand. |
| 3 | Asian Barometer Survey (ABS), Wave 1 (2005) | `data/raw/wave1_2005.xlsx` | [asianbarometer.org](https://www.asianbarometer.org) → Data → Merged Data Request (free, requires a short data-request form). Covers Nepal, India, Bangladesh, Sri Lanka, Pakistan — no Bhutan. |
| 4 | Asian Barometer Survey (ABS), Wave 2 (2013) | `data/raw/wave2_2013.xlsx` | Same source and access process as Wave 1, second wave. |

**Why WGI is a manual download instead of an API call:** the classic
`api.worldbank.org/v2` endpoint no longer serves WGI's `.EST` indicators (it returns
*"the indicator was not found... may have been deleted or archived"*), and its
replacement (Data360) was in Beta and intermittently unreachable during the original
research. All other World Bank indicators used in this project (migration,
remittances, GDP, enrollment, unemployment) are unaffected and are still pulled
live via the classic API — see below.

**Why V-Dem and ABS are manual downloads:** V-Dem is a free bulk-file-only release
(no per-query API); ABS's individual-level microdata is behind a free but
registration-gated data-request form, not an API.

Any file may be `.csv`, `.xlsx`, or `.xls` — `src/preprocessing.load_wgi_manual`
picks the reader based on the file extension. If your download comes with a
different filename (e.g. `wgidataset.xlsx`, or a V-Dem file with a version suffix
like `V-Dem-CY-Full+Others-v16.csv`), either rename it to match the table above or
edit the corresponding `*_RAW_PATH` constant in `src/config.py`.

## Fetched automatically (no download needed)

Migration, remittance, and socio-economic indicators are pulled live from the World
Bank's classic WDI API (`api.worldbank.org/v2`) by `src/preprocessing.fetch_worldbank`
every time `scripts/preprocess.py` / `scripts/run_pipeline.py` runs — net migration
(`SM.POP.NETM`), migrant stock (`SM.POP.TOTL`), personal remittances
(`BX.TRF.PWKR.CD.DT`, `BX.TRF.PWKR.DT.GD.ZS`), GDP per capita, secondary net
enrollment, and youth unemployment. No API key is required.

## `data/processed/` — pipeline outputs

Running `scripts/preprocess.py` (or the full `scripts/run_pipeline.py`) writes two
files here, which everything downstream (analysis, figures) reads back in:

- **`south_asia_panel.csv`** — the master country-year panel (WGI + V-Dem +
  World Bank migration/socio-economic indicators), Nepal + 5 South Asian
  comparators, 1996-2024.
- **`abs_respondent_level.csv`** — Asian Barometer respondent-level data, both
  waves, harmonized onto common numeric scales (trust, condition, regime
  preference, satisfaction with democracy).

Neither is committed to version control; both are cheap to regenerate from the raw
files above.

## Other sources considered but not loaded

A few sources were evaluated during the original research and deliberately left out
of this pipeline — kept here for context in case the project is extended:

| Source | Would give you | Why it's out of scope here |
|---|---|---|
| Global Data Lab Subnational HDI (SHDI) | District-level HDI/education/income, 1990-2022, all 6 countries | Needed for a sub-national extension (RQ2), not the country-year panel this pipeline builds. Free registration: `globaldatalab.org/shdi/download`. |
| Nepal DoFE district labor-permit series | District-wise realized labor migration, Nepal only | Same sub-national scope boundary as above; typically PDF/table extraction from `dofe.gov.np` annual reports. |
| Asia Foundation "Survey of the Nepali People" | Trust by federal/provincial/local government, by province — Nepal-only, denser | Nepal-only; would need its own harmonization work against the ABS province codes. |
| World Values Survey | Individual-level trust/values, same category as ABS | Nepal isn't fielded consistently across WVS waves. |

If any of these are added later, note that ABS province/region codes, SHDI's
`GDLCODE` district identifiers, and pre-2015 Nepali district names do not line up
automatically after Nepal's 2015 federal restructuring — that crosswalk would be its
own task.
