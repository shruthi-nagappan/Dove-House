External public data (non–Indiana MPH Hub)
========================================
Static reference for files under data_by_criteria/. Replace CSVs/PDFs manually when you refresh from agency sites.

Typical layout (criterion folders)
----------------------------------
- 01_economic_housing_stress/census_acs/ — ACS 5-year Indiana county tables (income, poverty, tenure, rent, female pop).
- 04_substance_use_overdose/cdc/ — Data.CDC.gov exports (county drug poisoning, VSRR IN, state, monthly causes).
- 06_rural_urban_service_gaps/cdc/ — Urban–rural provisional overdose (dtm2-meqi).
- 06_rural_urban_service_gaps/tiger_boundaries/ — TIGER/GENZ shapefile ZIPs.
- 03_safety_domestic_violence/icadv_reference/ — ICADV HTML snapshots (narrative; not a shelter GIS layer).
- 07_childcare_family_policy/indiana_dcs/ — Indiana DCS PDFs from in.gov.

Often obtained manually (portals / terms / bot limits)
------------------------------------------------------
- HUD CHAS — https://www.huduser.gov/portal/datasets/cp.html
- HUD PIT / CoC — https://www.hudexchange.info/
- Eviction Lab — https://data-downloads.evictionlab.org/
- SAMHSA / SAMHDA — agency portals and ICPSR studies
- OpenStreetMap Indiana — https://download.geofabrik.de/north-america/us/indiana-latest.osm.pbf

Rebuild warehouse after replacing files
---------------------------------------
  cd "<project root>"
  python3 scripts/ingest_all_downloaded_data_to_sqlite.py

Optional Census API key for future pulls: https://api.census.gov/data/key_signup.html
