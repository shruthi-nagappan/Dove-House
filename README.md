# Dove Recovery House — 4th Center Site Selection Analysis

> **Where in Indiana should Dove Recovery House build next to maximize impact for women most in need?**

This repository contains the full data pipeline, analytical scripts, Power BI-ready datasets, and interactive dashboard for the site selection analysis presented to **Dove Recovery House for Women** — a nonprofit providing trauma-informed, women-only recovery housing to Indiana women battling substance use disorders.

This project was developed by the **AI and Natural Language Processing Lab at Indiana University Bloomington**.

---

## The Problem

Dove Recovery House currently operates in **Marion County (Indianapolis)**, **Dubois County (Jasper)**, and **Bartholomew County (Columbus)**. Leadership needed a rigorous, data-driven framework to identify the ideal Indiana county for their **4th center** — one that maximizes reach to women with the greatest unmet need.

---

## Key Findings

| Rank | County | Composite Score |
|------|--------|----------------|
| #1 | **Blackford County** | 57.3 / 100 |
| #2 | Fayette County | 55.8 / 100 |
| #3 | Grant County | 55.7 / 100 |

These counties rose to the top consistently across every analytical lens and held their ranking even when stakeholders adjusted priorities using 14 interactive weight sliders.

---

## The Scale of Need

- Indiana's drug overdose death rate among women: **24.20 per 100,000**
- For women aged 20–44: **33.3 per 100,000** — a statewide emergency with a rural core
- Only **26 opioid treatment programs** serve all 92 Indiana counties
- Some women face **75-minute drives** to reach the nearest clinic

---

## Dashboard & Analysis

The analysis produced **7 analytical dashboards** across **25+ data sources** and **43+ custom measures**, covering:

| Dimension | What We Measured |
|---|---|
| **Overdose Mortality** | CDC county-level drug poisoning deaths, year by year |
| **OTP Access Gap** | Drive time to nearest opioid treatment program per county |
| **Women's Economic Stress** | 12 indicators: poverty, uninsurance, rent burden, unemployment, single-mother households |
| **Mental Health Burden** | Mental health EMS/ED events per 100k residents (MPH Hub 2017–2024) |
| **OD Touchpoints** | ED visits, EMS encounters, jail bookings, PDMP records, naloxone distribution |
| **Target Population** | Female population share, demographics, rural/urban classification |
| **Composite Need Score** | Weighted index combining all dimensions (0–100 scale, gender-adjusted) |

An interactive HTML dashboard with all 92 counties is available at [`powerbi_ready/dove_house_consolidated_dashboard.html`](powerbi_ready/dove_house_consolidated_dashboard.html).

---

## Repository Structure

```
data_by_criteria/
├── data_by_criteria/          # Raw source data (by analytical dimension)
│   ├── 01_economic_housing_stress/      # ACS poverty, income, rent, labor force
│   ├── 02_access_health_social_services/# Hospital discharges, OTP locations, drive times
│   ├── 04_substance_use_overdose/       # CDC mortality, OD touchpoints, prescriptions
│   ├── 05_structural_inequity_context/  # Mental health events by district
│   └── 06_rural_urban_service_gaps/     # USDA typology, rural/urban, TIGER boundaries
│
├── powerbi_ready/             # Cleaned, Power BI-ready CSVs (output of pipeline)
│   ├── 00_master_county_metrics.csv     # Primary fact table — 92 counties, 25 metrics
│   ├── 01_county_base.csv               # Population & demographics
│   ├── 02_county_socioeconomic.csv      # Income, poverty, unemployment, insurance
│   ├── 03a_county_overdose_latest.csv   # Most recent CDC overdose rate
│   ├── 03b_county_overdose_timeseries.csv # Historical overdose rates by year
│   ├── 04_otp_locations.csv             # 26 OTP facilities with lat/lon
│   ├── 05_county_otp_drive_time.csv     # Drive time to nearest OTP per county
│   ├── 06_county_mental_health_events.csv # MH EMS/ED events per 100k by year
│   ├── 07_county_composite_score.csv    # Normalized scores + final composite rank
│   ├── indiana_topo.json                # Indiana county TopoJSON (for Power BI Shape Map)
│   └── dove_house_consolidated_dashboard.html  # Standalone interactive dashboard
│
├── scripts/                   # Data pipeline scripts
│   ├── clean_for_powerbi.py             # Step 1: raw → 7 intermediate CSVs
│   ├── build_consolidated_dashboard.py  # Step 2: merge → master CSV + HTML dashboard
│   ├── make_indiana_topojson.py         # Convert TIGER shapefile → Indiana GeoJSON
│   ├── convert_to_topojson.py           # GeoJSON → TopoJSON for Power BI Shape Map
│   ├── validate_gender_adjustment.py    # Audit gender-adjustment impact by county
│   └── build_honest_v1_county_db.py     # SQLite data warehouse builder
│
├── datawarehouse/             # Intermediate SQLite exports
├── IndianaHospitalDischarges/ # Hospital discharge ontology & analysis
├── Dove_House_Dashboard_Handover.md     # Full Power BI setup guide (DAX, layout, gotchas)
└── README.md
```

---

## Composite Score Methodology

Each raw metric is **min-max normalized to 0–100** (higher = greater need), then combined with empirically-grounded weights:

| Component | Weight |
|---|---|
| Overdose Rate (CDC) | 25% |
| OTP Access Gap (drive time) | 20% |
| Women's Poverty Rate | 20% |
| Single-Mother Households | 15% |
| Unemployment Rate | 10% |
| Uninsured Rate | 5% |
| Mental Health Events | 5% |

**Gender adjustment:** Metrics sourced from gender-neutral population data (overdose rate, mental health events, poverty, unemployment, uninsured) are multiplied by each county's female population share. This corrects upward bias in counties with large male-dominated institutions (e.g. prisons), ensuring the score reflects conditions for women specifically.

**Mental health aggregation:** Mental health EMS/ED events are averaged across all available years (2017–2024) rather than using only the most recent year, avoiding partial-year data distortion in small counties.

---

## Reproducing the Pipeline

### Prerequisites
```
pip install pandas geopandas shapely topojson pyshp
```

### Step 1 — Generate Power BI-ready CSVs
```bash
python scripts/clean_for_powerbi.py
```
Outputs 7 CSVs to `powerbi_ready/`.

### Step 2 — Build master table + HTML dashboard
```bash
python scripts/build_consolidated_dashboard.py
```
Outputs `powerbi_ready/00_master_county_metrics.csv` and `powerbi_ready/dove_house_consolidated_dashboard.html`.

### Step 3 — Generate Indiana map geometry (one-time)
```bash
python scripts/make_indiana_topojson.py
python scripts/convert_to_topojson.py
```
Outputs `powerbi_ready/indiana_topo.json` for use in Power BI's Shape Map visual.

For full Power BI setup instructions (DAX measures, field parameters, bookmarks, button toggle), see [`Dove_House_Dashboard_Handover.md`](Dove_House_Dashboard_Handover.md).

---

## Existing Dove House Locations

| County | FIPS | City | Composite Score |
|---|---|---|---|
| Marion County | 18097 | Indianapolis | — |
| Dubois County | 18037 | Jasper | — |
| Bartholomew County | 18005 | Columbus | — |

All maps and analyses mark these counties to provide context for geographic coverage gaps.

---

## Team

Presented to Dove Recovery House for Women in Jasper, Indiana.

**AI and Natural Language Processing Lab — Indiana University Bloomington**

- **Naishal Shah** — Data pipeline, composite score methodology, Power BI dashboard
- **Shruthi Nagappan** — Dashboard development, data sourcing
- **Amy Stafford** — Analysis, co-presentation
- **Professor Damir Cavar** — Faculty advisor
- **Professor Danny Valdez** — Faculty advisor
- **Megan Durlauf** — Dove Recovery House, project coordination

---

## Data Sources

| Source | Data Provided |
|---|---|
| [CDC WONDER](https://wonder.cdc.gov/) | County-level drug poisoning mortality rates |
| [US Census ACS 5-Year](https://www.census.gov/programs-surveys/acs.html) | Poverty, income, unemployment, insurance, demographics |
| [Indiana MPH Hub](https://www.in.gov/mph/) | OTP drive times, mental health EMS/ED events, OD touchpoints |
| [SAMHSA OTP Locator](https://www.samhsa.gov/) | OTP facility locations (26 programs statewide) |
| [USDA ERS County Typology](https://www.ers.usda.gov/) | Rural/urban classification for all Indiana counties |
| [Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) | Indiana county boundary shapefiles |

---

*This analysis was conducted for nonprofit planning purposes. Data reflects publicly available sources. For questions, contact the IU NLP Lab.*
