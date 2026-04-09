Dove Recovery House — data_by_criteria/
======================================
Raw and processed public data files are grouped to match the “Data Sources” slide themes (Power BI joins often use county_fips / FIPS).

01_economic_housing_stress
  census_acs/          — ACS 5-year county: income, poverty, tenure, rent, female pop (Honest v1 denominator context).
  acs_extended/        — DP03, B23025, B11002/B11005 (extra ACS county tables).

02_access_health_social_services
  mph_hub/              — MPH Hub: OTP locations/drive time, EMS runs, mental-health EMS/ED by county.
  indiana_hospital_discharge/ — IDOH-style discharge CSVs + script outputs (substance abuse extracts).
  opioid_treatment_program_locations/ — standalone OTP CSV if copied here.

03_safety_domestic_violence
  icadv_reference/      — ICADV HTML snapshots (links / narrative; not a shelter GIS layer).

04_substance_use_overdose
  cdc/                  — CDC Data.CDC.gov: county drug poisoning, VSRR Indiana, state file, monthly causes.
  mph_hub/              — OD touchpoints, opioid Rx / fatal OD relationship, Rx by provider.

05_structural_inequity_context
  mph_hub/              — Mental-health EMS/ED by district (and similar).

06_rural_urban_service_gaps
  cdc/                  — Urban–rural provisional overdose (dtm2-meqi).
  tiger_boundaries/     — TIGER / GENZ shapefile ZIPs.
  usda_county_typology/ — USDA ERS typology (cg_ers_typology_*).
  README_criteria_gap_sources.txt — notes on these extra sources.

07_childcare_family_policy
  indiana_dcs/          — DCS PDFs (org chart, regional map).

08_pipeline_logs_and_readme
  _fetch_log.json, external_public_data_README.txt — notes from when data was last refreshed (optional).

Honest v1 note
--------------
County overdose/mortality tables are all-sex (CDC). Female population shares come from ACS — not women-only overdose numerators unless you add another source.

Scripts (local processing only; raw CSVs live in this tree)
------------------------------------------------------------
  scripts/ingest_all_downloaded_data_to_sqlite.py  — load files → datawarehouse/dove_house_all_data.sqlite
  scripts/build_honest_v1_county_db.py             — CDC + ACS → dove_house_honest_v1.sqlite + mart CSV
  scripts/query_county_overdose_female_context.py — join example → python_county_overdose_female_context.csv
  scripts/explore_databases.py                      — inspect SQLite
