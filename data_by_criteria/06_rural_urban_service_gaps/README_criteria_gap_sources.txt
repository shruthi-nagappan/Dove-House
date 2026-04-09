Criteria-gap datasets (public)
==============================
These files extend slide-criteria coverage:

- Rural / metro / economic structure: USDA ERS typology (Metro2023 + ERS flags).
  Files: cg_ers_typology_2025_us_all.csv (US), cg_ers_typology_2025_in.csv (Indiana rows only).
- Employment & uninsured (context): ACS Data Profile DP03 selected fields.
  File: acs_in_counties_dp03_insurance_unemployment_2023.csv
- Labor force counts: ACS B23025.
  File: acs_in_counties_b23025_labor_force_2023.csv
- Household structure proxies: ACS B11002 / B11005.
  File: acs_in_counties_b11002_b11005_households_2023.csv

ACS 5-year vintage matches API year (2023 release ≈ 2019–2023). Confirm column meanings in Census documentation.

Still missing (cannot fully automate here)
-------------------------------------------
- Eviction counts / filings (Eviction Lab partial; courts vary).
- HUD CHAS housing problems (often browser download; HUD User may block scripts).
- HUD PIT / CoC homeless counts (HUD Exchange; manual per year).
- IPV/DV shelter capacity / rates (coalition lists, state reports).
- Suicide mortality by sex/county (often CDC WONDER interactive + suppression).
- Child welfare outcomes (DCS published reports + formal requests).
- Regenstrief / INPC (agreements).
- APRA / Hoosier by Numbers (workflow, not a URL).

Re-load into SQLite
-------------------
  python3 scripts/ingest_all_downloaded_data_to_sqlite.py

