# Dove House Power BI — Colleague Handover Document

## Purpose

This document explains everything built for the **"Dove House Recovery — 4th Center Site Analysis"** consolidated dashboard page. It covers the full data pipeline, the Power BI tables, all DAX measures, and how the visuals are wired together — so a colleague can pick up, maintain, or extend the work.

---

## Part 1 — Data Pipeline (How the CSVs Were Made)

All source data lives in:
`data_by_criteria/data_by_criteria/` (raw)
`data_by_criteria/powerbi_ready/` (cleaned, Power BI-ready)

### Raw Sources

| Source | What it provides |
|---|---|
| CDC (drug poisoning mortality) | Overdose death rate ranges by Indiana county (2015, county-level) |
| US Census ACS 5-year | Poverty rate, median household income, unemployment, uninsured rate, single-mother households, rent burden, female population |
| Indiana MPH Hub | Opioid Treatment Program (OTP) drive times by county; mental health EMS/ED events per 100k |
| SAMHSA OTP Locator | OTP facility names, addresses, lat/lon coordinates |
| TIGER/Line shapefiles (Census) | Indiana county boundaries for mapping |

### Step 1 — `clean_for_powerbi.py`

Reads raw source files and outputs 7 intermediate CSVs to `powerbi_ready/`:

| Output File | Contents |
|---|---|
| `01_county_base.csv` | 92 counties, population demographics |
| `02_county_socioeconomic.csv` | Income, poverty, unemployment, insurance, rent burden |
| `03a_county_overdose_latest.csv` | Most recent CDC overdose rate (2015) |
| `03b_county_overdose_timeseries.csv` | Historical overdose rates by year |
| `04_otp_locations.csv` | OTP facility point data (26 facilities, lat/lon) |
| `05_county_otp_drive_time.csv` | Min/avg/max drive time to nearest OTP per county |
| `06_county_mental_health_events.csv` | Mental health EMS/ED events per 100k by year |
| `07_county_composite_score.csv` | Normalized component scores + final composite rank/score |

**Composite Score formula (in `clean_for_powerbi.py`):**
Each component is min-max scaled to 0–100, then combined with these weights:
- Overdose Rate: 25%
- OTP Access Gap (drive time): 20%
- Women's Poverty Rate: 20%
- Single Mothers: 15%
- Unemployment: 10%
- Uninsured Rate: 5%
- Mental Health Events: 5%

Ranking: `county_rank = 1` = highest need county statewide.

### Step 2 — `build_consolidated_dashboard.py`

Merges the 7 intermediate CSVs into one flat table and writes:

**`powerbi_ready/00_master_county_metrics.csv`** — 92 rows (one per Indiana county), 25 columns:

| Column | Description |
|---|---|
| `county_fips` | 5-digit FIPS string (e.g. "18097") — primary join key |
| `county_name` | County name |
| `county_rank` | Overall composite rank (1 = highest need, 92 = lowest) |
| `composite_need_score` | Weighted composite score (0–100) |
| `is_dove_house` | Boolean — True for Marion, Dubois, Bartholomew |
| `overdose_rate_midpoint` | CDC drug poisoning deaths per 100k |
| `rate_range` | CDC reported range string |
| `min_drive_time_min` | Minutes to nearest OTP (minimum) |
| `avg_drive_time_min` | Minutes to nearest OTP (average) |
| `otp_access_tier` | Categorical access tier |
| `poverty_rate_pct` | Female poverty rate % (ACS) |
| `median_hh_income` | Median household income |
| `single_mother_pct` | Single-mother household % |
| `unemployment_rate_pct` | Unemployment rate % |
| `uninsured_rate_pct` | Uninsured rate % |
| `rent_burden_30pct_rate` | % paying >30% income on rent |
| `mh_events_per_100k` | Mental health EMS/ED events per 100k |
| `self_harm_per_100k` | Self-harm events per 100k |
| `n_overdose` | Normalized overdose score (0–100) |
| `n_drive_time` | Normalized OTP drive time score (0–100) |
| `n_poverty` | Normalized poverty score (0–100) |
| `n_single_mom` | Normalized single-mother score (0–100) |
| `n_unemployment` | Normalized unemployment score (0–100) |
| `n_uninsured` | Normalized uninsured score (0–100) |
| `n_mh_events` | Normalized mental health score (0–100) |

### Step 3 — Indiana Map Geometry

Two Python scripts convert the TIGER shapefile to Power BI's required format:

**`scripts/make_indiana_topojson.py`**
- Reads: `data_by_criteria/06_rural_urban_service_gaps/tiger_boundaries/cb_2022_us_county_500k.zip`
- Filters to Indiana counties only (STATEFP == "18")
- Outputs: `powerbi_ready/indiana_counties.json` (GeoJSON, 92 counties, feature id = FIPS string)

**`scripts/convert_to_topojson.py`**
- Reads: `powerbi_ready/indiana_counties.json`
- Converts to TopoJSON format (required by Power BI Shape Map visual)
- Preserves GEOID as geometry id for map matching
- Outputs: `powerbi_ready/indiana_counties.topojson`
- Also saved as: `powerbi_ready/indiana_topo.json` (.json extension — Power BI file browser only accepts .json)

---

## Part 2 — Power BI Dashboard Setup

### Tables Imported

**CountyMetrics table**
- Source: `powerbi_ready/00_master_county_metrics.csv`
- Home → Get Data → Text/CSV → select file
- In Power Query: set `county_fips` column type → **Text** (critical — prevents FIPS from loading as a number and breaking map joins)
- Renamed table: `CountyMetrics`

**OTPLocations table**
- Source: `powerbi_ready/04_otp_locations.csv`
- Same import steps; `county_fips` → Text
- Renamed table: `OTPLocations`
- Used for: OTP facility point map layer

**DoveHouseLocations table** (created manually — Enter Data)
- Home → Enter Data
- 3 rows:

| county_fips | location_name | lat | lon |
|---|---|---|---|
| 18097 | Marion County (Indy) | 39.7684 | -86.1581 |
| 18037 | Dubois County (Jasper) | 38.3917 | -86.9311 |
| 18005 | Bartholomew Co. (Columbus) | 39.2014 | -85.9214 |

### Map Layer Table (Field Parameter)

- Modeling tab → **New Parameter → Fields**
- Name: `Map Layer`
- Added 6 measures in this order (order matters — sets the `Map Layer Order` index 0–5):
  1. `[Composite Need Score]`
  2. `[Overdose Rate per 100k]`
  3. `[OTP Drive Time (min)]`
  4. `[Women in Poverty %]`
  5. `[MH Events per 100k]`
  6. `[Socioeconomic Index]`
- Checked "Add slicer to this page" → Create

Power BI auto-generates the `Map Layer` table with:
- `Map Layer Fields` — the measure reference (used in Color Saturation of the Shape Map)
- `Map Layer Order` — integer 0–5 (used in SWITCH DAX logic)

The slicer from this step is hidden (placed off-canvas) — the 6 buttons control it via bookmarks.

---

## Part 3 — DAX Measures (all in CountyMetrics table)

Created via: select `CountyMetrics` table → Home → New Measure

### Layer Measures (drive the map and bar chart)

```dax
Composite Need Score = AVERAGE(countyMetrics[composite_need_score])

Overdose Rate per 100k = AVERAGE(countyMetrics[overdose_rate_midpoint])

OTP Drive Time (min) = AVERAGE(countyMetrics[min_drive_time_min])

Women in Poverty % = AVERAGE(countyMetrics[poverty_rate_pct])

MH Events per 100k = AVERAGE(countyMetrics[mh_events_per_100k])

Socioeconomic Index =
    AVERAGEX(
        countyMetrics,
        (countyMetrics[n_poverty] + countyMetrics[n_uninsured] + countyMetrics[n_unemployment]) / 3
    )
```

### Dynamic Description Card

```dax
Layer Description =
SWITCH(
    SELECTEDVALUE('Map Layer'[Map Layer Order]),
    0, "Composite Need Score: weighted index combining overdose risk, service gaps, poverty, and mental health (0–100 scale)",
    1, "Overdose Rate: CDC drug poisoning deaths per 100,000 residents (2015)",
    2, "OTP Drive Time: minutes to nearest opioid treatment program",
    3, "Women in Poverty %: female residents below poverty line (ACS)",
    4, "MH Events per 100k: mental health EMS/ED events (MPH Hub 2017–2024)",
    5, "Socioeconomic Index: combined normalized poverty, uninsured, unemployment score",
    "Select a layer"
)
```

### KPI Cards (fixed to composite score)

```dax
Top Recommended County =
CALCULATE(MAX(countyMetrics[county_name]), countyMetrics[county_rank] = 1)

Indiana Avg Score = ROUND(AVERAGE(countyMetrics[composite_need_score]), 1)

High Need Counties =
COUNTROWS(FILTER(countyMetrics, countyMetrics[composite_need_score] >= 45))
```

### Existing Location Cards

```dax
Marion Composite Score =
CALCULATE(AVERAGE(countyMetrics[composite_need_score]), countyMetrics[county_fips] = "18097")

Dubois Composite Score =
CALCULATE(AVERAGE(countyMetrics[composite_need_score]), countyMetrics[county_fips] = "18037")

Bartholomew Composite Score =
CALCULATE(AVERAGE(countyMetrics[composite_need_score]), countyMetrics[county_fips] = "18005")
```

---

## Part 4 — Visuals & Layout

### Shape Map (Indiana Choropleth)
- Visual: Shape Map
- Location field: `county_fips` from `CountyMetrics`
- Color Saturation field: `Map Layer Fields` from the `Map Layer` parameter table
- Custom map: Format → Shape → Add map → `powerbi_ready/indiana_topo.json`
- Projection: Mercator (not Orthographic — that renders blank)
- Color scheme: Sequential Blues

### Top 15 Bar Chart
- Visual: Bar chart
- Y-axis: `county_name`
- X-axis: `Map Layer Fields`
- Filter: `county_rank` is less than or equal to 15 (applied via Filters pane — Top N filter did not work with Field Parameters, so static rank filter used instead)
- Sort: descending by value

### Existing Dove House Locations Table
- Visual: Table
- Columns: `county_name`, composite score measure, `county_rank`
- Filtered to Marion (18097), Dubois (18037), Bartholomew (18005)

### Layer Description Card
- Visual: Card
- Callout value: `[Layer Description]`
- Font size reduced to 11, Word wrap enabled (text is long)

### KPI Cards (3 cards)
- Top Recommended County (`[Top Recommended County]`)
- Indiana Avg Score (`[Indiana Avg Score]`)
- High Need Counties (`[High Need Counties]`)

---

## Part 5 — Button/Bookmark Layer Toggle

### Bookmarks (6 total)
Created via View → Bookmarks panel → Add bookmark for each layer:

| Bookmark Name | Map Layer slicer set to |
|---|---|
| BM_Composite | Composite Need Score |
| BM_Overdose | Overdose Rate per 100k |
| BM_OTP | OTP Drive Time (min) |
| BM_Population | Women in Poverty % |
| BM_MentalHealth | MH Events per 100k |
| BM_Socioeconomic | Socioeconomic Index |

Bookmark settings: **Data checked, Display unchecked, Current page unchecked** (captures slicer state only, not visual positions).

### Buttons (6 total)
- Insert → Buttons → Blank (×6, arranged in a row below the header)
- Labels: `Composite Score`, `Overdose Demand`, `OTP Access Gap`, `Target Population`, `Mental Health`, `Socioeconomic`
- Format → Action → Type: Bookmark → select matching bookmark
- Style: navy fill (`#1B4F72`), white text

**Note:** In Power BI Desktop, buttons require **Ctrl+Click** to activate. After publishing to Power BI Service (app.powerbi.com), buttons work with a single click.

---

## Part 6 — Key Decisions & Gotchas

| Issue | Fix Applied |
|---|---|
| Shape Map blank with GeoJSON | Power BI Shape Map requires TopoJSON format. Converted with Python `topojson` library |
| TopoJSON .topojson extension rejected | Power BI file browser shows .json only. Saved copy as `indiana_topo.json` |
| county_fips loaded as number | Set column type to Text in Power Query before loading |
| Top N filter not working with Field Parameters | Known Power BI limitation. Used `county_rank <= 15` column filter instead |
| Map color grayed out | Caused by having `city` in Legend field. Removed city from Legend |
| Dynamic RANKX broken with Field Parameters | Deleted Dynamic Rank measure; used pre-computed `county_rank` column instead |

---

## Critical Files

| File | Role |
|---|---|
| `powerbi_ready/00_master_county_metrics.csv` | Primary fact table — 92 counties, all 25 metrics |
| `powerbi_ready/04_otp_locations.csv` | 26 OTP points with lat/lon for point layer |
| `powerbi_ready/07_county_composite_score.csv` | Composite score + component normalized scores |
| `data_by_criteria/06_rural_urban_service_gaps/tiger_boundaries/cb_2022_us_county_500k.zip` | TIGER shapefile — needs TopoJSON conversion for Shape Map visual |

---

## Step 0 — Convert Shapefile to Indiana TopoJSON

Power BI's **Shape Map visual** requires TopoJSON. Run this Python script once before opening Power BI:

```python
# scripts/make_indiana_topojson.py
import zipfile, shapefile, json, os

TIGER_ZIP = r"c:\Users\mrnai\Downloads\Dove House\data_by_criteria\data_by_criteria\06_rural_urban_service_gaps\tiger_boundaries\cb_2022_us_county_500k.zip"
OUT_FILE  = r"c:\Users\mrnai\Downloads\Dove House\data_by_criteria\powerbi_ready\indiana_counties.json"

# Extract shapefile
with zipfile.ZipFile(TIGER_ZIP) as z:
    z.extractall("_tiger_tmp")

# Read and filter to Indiana (STATEFP == "18")
sf = shapefile.Reader("_tiger_tmp/cb_2022_us_county_500k.shp")
fields = [f[0] for f in sf.fields[1:]]
features = []
for sr in sf.shapeRecords():
    rec = dict(zip(fields, sr.record))
    if rec.get("STATEFP") == "18":
        fips = rec["STATEFP"] + rec["COUNTYFP"]
        features.append({
            "type": "Feature",
            "id": fips,
            "properties": {"GEOID": fips, "NAME": rec["NAME"]},
            "geometry": sr.shape.__geo_interface__
        })

geojson = {"type": "FeatureCollection", "features": features}

# Power BI Shape Map needs a specific TopoJSON wrapper — write as GeoJSON first,
# then Power BI can accept GeoJSON directly in Shape Map (newer builds support it)
with open(OUT_FILE, "w") as f:
    json.dump(geojson, f)

print(f"Wrote {len(features)} Indiana counties → {OUT_FILE}")

# Cleanup
import shutil
shutil.rmtree("_tiger_tmp", ignore_errors=True)
```

Run: `python scripts/make_indiana_topojson.py`
Output: `powerbi_ready/indiana_counties.json` (92 Indiana counties, feature id = FIPS e.g. "18097")

---

## Step 1 — Open Power BI Desktop, Import Data

**File → New** (or open a fresh .pbix)

### 1a. Import master county metrics
- **Home → Get Data → Text/CSV**
- Select `powerbi_ready/00_master_county_metrics.csv`
- In Power Query: set `county_fips` column type → **Text** (critical — must be text like "18097", not number)
- Rename table → `CountyMetrics`
- Load

### 1b. Import OTP locations
- **Get Data → Text/CSV** → `powerbi_ready/04_otp_locations.csv`
- Columns needed: `facility_name`, `lat`, `lon`, `county_fips`, `city`
- Set `county_fips` → **Text**
- Rename table → `OTPLocations`
- Load

### 1c. Create Dove House locations table (manual — 3 rows)
- **Home → Enter Data**
- Create table named `DoveHouseLocations`:

| county_fips | location_name       | lat      | lon       |
|-------------|---------------------|----------|-----------|
| 18097        | Marion County (Indy) | 39.7684  | -86.1581  |
| 18037        | Dubois County (Jasper)| 38.3917 | -86.9311  |
| 18005        | Bartholomew Co. (Columbus)| 39.2014| -85.9214 |

- Load

---

## Step 2 — Set Up Data Model

Go to **Model view** (left rail).

- No relationships needed — `CountyMetrics` is a flat denormalized table with one row per county.
- `OTPLocations` and `DoveHouseLocations` are standalone point tables (not joined).

---

## Step 3 — Create the 6 Layer Measures

In `CountyMetrics` table, create these DAX measures (**Home → New Measure**):

```dax
[Composite Need Score] = AVERAGE(CountyMetrics[composite_need_score])

[Overdose Rate per 100k] = AVERAGE(CountyMetrics[overdose_rate_midpoint])

[OTP Drive Time (min)] = AVERAGE(CountyMetrics[min_drive_time_min])

[Women in Poverty %] = AVERAGE(CountyMetrics[poverty_rate_pct])

[MH Events per 100k] = AVERAGE(CountyMetrics[mh_events_per_100k])

[Socioeconomic Index] =
    AVERAGEX(
        CountyMetrics,
        (CountyMetrics[n_poverty] + CountyMetrics[n_uninsured] + CountyMetrics[n_unemployment]) / 3
    )
```

---

## Step 4 — Create a Field Parameter (Layer Switcher)

> Field Parameters (Power BI Feb 2022+) let a slicer control which measure the visual uses.

**Modeling tab → New Parameter → Fields**

- Name: `Map Layer`
- Add these 6 measures (in order):
  1. `[Composite Need Score]`
  2. `[Overdose Rate per 100k]`
  3. `[OTP Drive Time (min)]`
  4. `[Women in Poverty %]`
  5. `[MH Events per 100k]`
  6. `[Socioeconomic Index]`
- Check **"Add slicer to this page"**
- Click **Create**

Power BI creates a `Map Layer` table with a `Map Layer Fields` column and a `Map Layer Order` column. The slicer that appears will let the user pick which measure drives the map.

---

## Step 5 — Build the Dashboard Page Layout

Rename the page: `Dove House — Site Selection`

**Layout (approximate):**
```
┌──────────────────────────────────────────────────┐
│  DOVE HOUSE RECOVERY — 4th Center Site Analysis  │  ← text box header
├──────────┬───────────────────────────────────────┤
│ BUTTONS  │                                        │
│ [Comp ▼] │          INDIANA CHOROPLETH MAP        │
│ [OD Rx]  │              (Shape Map)               │
│ [OTP  ]  │                                        │
│ [Pop  ]  │   ● OTP locations (bubble layer)       │
│ [MH   ]  │   ★ Dove House existing (3 pins)       │
│ [SES  ]  │                                        │
├──────────┴──────────┬────────────────────────────┤
│  TOP 10 COUNTIES    │  SELECTED METRIC: [name]    │
│  (bar chart)        │  Description text box       │
└─────────────────────┴────────────────────────────┘
```

### 5a. Add the Shape Map visual
- **Visualizations pane → Shape Map** (if not visible: View → Enable Preview Features → Shape Map)
- **Location field**: drag `county_fips` from `CountyMetrics`
- **Color saturation field**: drag `Map Layer Fields` (from the `Map Layer` parameter table)
- **Format → Shape → Add map** → browse to `powerbi_ready/indiana_counties.json`
- Under Format → Map settings → choose your color scheme (recommend **Sequential Blues** for most layers, **Red-Green diverging** for Composite Score)

### 5b. Add OTP point bubbles
- Add a **Map visual** (not Shape Map — this one handles lat/lon)
- OR: overlay a second Shape Map is not possible — instead, note OTPs in a separate small visual

**Best approach:** Use **ArcGIS Maps for Power BI** or the standard **Map visual** for OTP points:
- Add a **Map visual** on top of the Shape Map (position: same area, transparent background)
- Latitude → `OTPLocations[lat]`, Longitude → `OTPLocations[lon]`
- Size: small fixed dot, color: orange
- This creates a point bubble layer stacked over the county map

### 5c. Add Dove House pins
- Add another **Map visual** for `DoveHouseLocations`
- Latitude → `DoveHouseLocations[lat]`, Longitude → `DoveHouseLocations[lon]`
- Legend → `location_name`
- Size: large, distinctive color (e.g. dark red / maroon)
- Format → Data labels → On (shows county name)

### 5d. Add the Top 10 bar chart
- Add a **Bar Chart** visual
- Axis: `county_name` (top 10 by filtered measure)
- Values: `Map Layer Fields` (the parameter measure)
- Filters: Top N filter → Top 10 by `Map Layer Fields`
- Sort: descending

### 5e. Add the metric description text box
- Add a **Text box** or **Card** showing which layer is active
- Use a DAX measure for the description:

```dax
[Layer Description] =
SWITCH(
    SELECTEDVALUE('Map Layer'[Map Layer Order]),
    0, "Composite Need Score: weighted index combining overdose risk, service gaps, poverty, and mental health burden (0–100)",
    1, "Overdose Rate: CDC drug poisoning mortality rate per 100,000 residents (2015 data, county-level)",
    2, "OTP Drive Time: minimum driving time in minutes to nearest opioid treatment program",
    3, "Women in Poverty %: share of female residents below federal poverty line (ACS 5-year)",
    4, "MH Events per 100k: mental health EMS/ED events per 100,000 residents (MPH Hub 2017–2024)",
    5, "Socioeconomic Index: combined normalized poverty + uninsured + unemployment score",
    "Select a layer above"
)
```

---

## Step 6 — Style the 6 Toggle Buttons

Instead of a slicer (dropdown), use **styled buttons** connected to bookmarks for a premium look:

### 6a. Create 6 bookmarks (one per layer)
- **View → Bookmarks panel → Add**
- For each bookmark:
  1. Set the slicer value (Map Layer) to the desired layer
  2. Capture the state (ensure "Data" is checked in bookmark options)
  3. Name: `BM_Composite`, `BM_Overdose`, `BM_OTP`, `BM_Population`, `BM_MentalHealth`, `BM_Socioeconomic`

### 6b. Add 6 button shapes
- **Insert → Buttons → Blank** (×6, arranged vertically on the left)
- Button labels: `Composite Score`, `Overdose Demand`, `OTP Access Gap`, `Target Population`, `Mental Health`, `Socioeconomic`
- **Format → Action → Type: Bookmark** → select the matching bookmark for each button
- Style: fill color = `#1B4F72` (dark navy), text = white, selected/hover state = `#2E86C1`

### 6c. Hide the auto-generated slicer
- The slicer from Step 4 drives the data — keep it but format it with zero opacity, or place it off-screen. The buttons control it via bookmarks.

---

## Step 7 — Color Scheme & Branding

| Element | Color |
|---|---|
| Page background | `#F8F9FA` (light gray) |
| Header bar | `#1B4F72` (dark navy) |
| Header text | White |
| Active button | `#2E86C1` (blue) |
| Inactive button | `#85929E` (gray) |
| Map choropleth (low) | `#EBF5FB` (pale blue) |
| Map choropleth (high) | `#1A5276` (deep blue) |
| OTP points | `#E67E22` (orange) |
| Dove House pins | `#C0392B` (red) |
| Bar chart fill | `#2E86C1` |
| Top 5 counties (bar) | `#1A5276` (darker) |

**Font:** Segoe UI (Power BI default — keep it)

---

## Step 8 — Existing Dove House counties callout card

Add 3 KPI cards or a table showing:
- Marion County (Rank #XX, Score XX) — **Existing location**
- Dubois County (Rank #XX, Score XX) — **Existing location**
- Bartholomew County (Rank #XX, Score XX) — **Existing location**

DAX measures:

```dax
[Marion Composite Score] =
CALCULATE(AVERAGE(CountyMetrics[composite_need_score]), CountyMetrics[county_fips] = "18097")

[Dubois Composite Score] =
CALCULATE(AVERAGE(CountyMetrics[composite_need_score]), CountyMetrics[county_fips] = "18037")

[Bartholomew Composite Score] =
CALCULATE(AVERAGE(CountyMetrics[composite_need_score]), CountyMetrics[county_fips] = "18005")
```

---

## Step 9 — Verification Checklist

Before sharing:
- [ ] All 92 Indiana counties appear colored on the map (no gray/missing counties)
- [ ] Each of the 6 buttons changes the map color and bar chart
- [ ] 26 OTP orange dots visible on the map
- [ ] 3 Dove House red pins visible (Marion, Dubois, Bartholomew)
- [ ] Blackford County appears as #1 on Composite Score view
- [ ] Top 10 bar chart updates when layer switches
- [ ] Layer description card updates with each button click
- [ ] Marion County (Indianapolis) shows near-zero OTP drive time (it's dense)

---

## Save As

Save the new file as:
`c:\Users\mrnai\Downloads\Dove House\Dove_House_Site_Selection_v1.pbix`

Keep `dove house updated.pbix` untouched as the backup.
