"""
build_consolidated_dashboard.py
Dove House — Single-page interactive HTML dashboard.
One Indiana map, 6 toggle buttons for different data layers.

Run from the data_by_criteria root:
    python scripts/build_consolidated_dashboard.py

Output:
    powerbi_ready/dove_house_consolidated_dashboard.html
"""

import zipfile, io, json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path("c:/Users/mrnai/Downloads/Dove House/data_by_criteria")
OUT  = ROOT / "powerbi_ready"
OUT.mkdir(exist_ok=True)

print("Building Dove House Consolidated Dashboard...")

# ─── 1. LOAD DATA ─────────────────────────────────────────────────────────────
score  = pd.read_csv(OUT / "07_county_composite_score.csv", dtype={"county_fips": str})
socio  = pd.read_csv(OUT / "02_county_socioeconomic.csv",  dtype={"county_fips": str})
otp    = pd.read_csv(OUT / "04_otp_locations.csv",         dtype={"county_fips": str})
drive  = pd.read_csv(OUT / "05_county_otp_drive_time.csv", dtype={"county_fips": str})
mh_raw = pd.read_csv(OUT / "06_county_mental_health_events.csv", dtype={"county_fips": str})

# Mental health: most recent year per county
mh = (mh_raw.sort_values("year", ascending=False)
            .groupby("county_fips", as_index=False)
            .first()[["county_fips", "mh_events_per_100k", "self_harm_per_100k"]])

# Master table — score already contains most metrics; pull only new columns
master = (score
    .merge(socio[["county_fips", "median_hh_income", "rent_burden_30pct_rate"]], on="county_fips", how="left")
    .merge(drive[["county_fips", "avg_drive_time_min"]], on="county_fips", how="left")
    .merge(mh[["county_fips", "self_harm_per_100k"]], on="county_fips", how="left")
)
master["mh_events_per_100k"] = master["mh_events_per_100k"].fillna(0)

# Existing Dove House county centroids
DOVE_LOCS = pd.DataFrame([
    {"label": "Dove House — Marion Co.",      "fips": "18097", "lat": 39.768, "lon": -86.158},
    {"label": "Dove House — Dubois Co.",      "fips": "18037", "lat": 38.369, "lon": -86.898},
    {"label": "Dove House — Bartholomew Co.", "fips": "18005", "lat": 39.206, "lon": -85.929},
])
master["is_dove_house"] = master["county_fips"].isin(DOVE_LOCS["fips"])

print(f"  Master table: {len(master)} counties, {len(master.columns)} cols")

# ─── 2. INDIANA GEOJSON FROM TIGER SHAPEFILE ──────────────────────────────────
import shapefile as sf

SHP_ZIP = (ROOT / "data_by_criteria/06_rural_urban_service_gaps/tiger_boundaries"
           / "cb_2022_us_county_500k.zip")

with zipfile.ZipFile(SHP_ZIP) as z:
    shp_bytes = io.BytesIO(z.read("cb_2022_us_county_500k.shp"))
    dbf_bytes = io.BytesIO(z.read("cb_2022_us_county_500k.dbf"))

reader = sf.Reader(shp=shp_bytes, dbf=dbf_bytes)
fields = [f[0] for f in reader.fields[1:]]

features = []
for sr in reader.shapeRecords():
    rec = dict(zip(fields, sr.record))
    if str(rec.get("STATEFP", "")) != "18":
        continue
    geoid = str(rec.get("GEOID", ""))
    features.append({
        "type": "Feature",
        "id": geoid,
        "properties": {"GEOID": geoid, "NAME": rec.get("NAME", "")},
        "geometry": sr.shape.__geo_interface__,
    })

indiana_geojson = {"type": "FeatureCollection", "features": features}
print(f"  Indiana GeoJSON: {len(features)} counties")

# ─── 3. LAYER DEFINITIONS ─────────────────────────────────────────────────────
LAYERS = [
    {
        "key":    "composite_need_score",
        "label":  "Composite Need Score",
        "desc":   "Weighted index (0–100) combining overdose rate, OTP access gap, poverty, single mothers, unemployment, uninsured, and mental health events",
        "color":  [[0,"#FFF5F5"],[0.25,"#FEB2B2"],[0.5,"#FC8181"],[0.75,"#E53E3E"],[1,"#742A2A"]],
        "unit":   "score",
    },
    {
        "key":    "overdose_rate_midpoint",
        "label":  "Drug Overdose Rate",
        "desc":   "Age-adjusted drug overdose death rate per 100k population (CDC, 2015 — most recent county-level data available)",
        "color":  [[0,"#FFF5EB"],[0.25,"#FDD0A2"],[0.5,"#FDA761"],[0.75,"#E6550D"],[1,"#7F2704"]],
        "unit":   "per 100k",
    },
    {
        "key":    "min_drive_time_min",
        "label":  "OTP Access Gap",
        "desc":   "Minimum drive time (minutes) from any ZIP code in the county to the nearest Opioid Treatment Program — darker means farther away",
        "color":  [[0,"#FFFDE7"],[0.25,"#FFF176"],[0.5,"#FFB300"],[0.75,"#E65100"],[1,"#BF360C"]],
        "unit":   "min drive",
    },
    {
        "key":    "poverty_rate_pct",
        "label":  "Women & Poverty",
        "desc":   "County poverty rate (%) — ACS 2023. A key driver of housing instability and barriers to accessing substance use treatment for women",
        "color":  [[0,"#FFF0F6"],[0.25,"#FBB6CE"],[0.5,"#F687B3"],[0.75,"#B83280"],[1,"#702459"]],
        "unit":   "%",
    },
    {
        "key":    "mh_events_per_100k",
        "label":  "Mental Health Events",
        "desc":   "Mental health-related EMS/ED events per 100k population (most recent year, Indiana MPH Hub) — proxy for unmet mental health and substance use crisis burden",
        "color":  [[0,"#F5F3FF"],[0.25,"#C4B5FD"],[0.5,"#8B5CF6"],[0.75,"#6D28D9"],[1,"#3B0764"]],
        "unit":   "per 100k",
    },
    {
        "key":    "unemployment_rate_pct",
        "label":  "Socioeconomic Stress",
        "desc":   "Unemployment rate (%) — ACS 2023. Alongside rent burden and uninsured rates, signals counties where economic hardship compounds substance use risk",
        "color":  [[0,"#EBF8FF"],[0.25,"#90CDF4"],[0.5,"#4299E1"],[0.75,"#2B6CB0"],[1,"#1A365D"]],
        "unit":   "%",
    },
]
N_LAYERS = len(LAYERS)

# ─── 4. HOVER TEXT ────────────────────────────────────────────────────────────
def fmt_val(v, unit):
    if pd.isna(v):
        return "N/A"
    if unit == "%":
        return f"{v:.1f}%"
    elif unit == "score":
        return f"{v:.1f}"
    elif "100k" in unit:
        return f"{v:,.0f}"
    else:
        return f"{v:.0f} min"

def build_hover(row):
    dove = "<br><b>★ Existing Dove House Center</b>" if row["is_dove_house"] else ""
    return (
        f"<b>{row['county_name']}</b>{dove}<br>"
        f"<b>Rank #{int(row['county_rank'])}  |  Need Score: {row['composite_need_score']:.1f}</b><br>"
        f"───────────────────<br>"
        f"Overdose Rate: {fmt_val(row['overdose_rate_midpoint'], 'per 100k')} per 100k<br>"
        f"OTP Drive Time: {fmt_val(row['min_drive_time_min'], 'min')} ({row.get('otp_access_tier','N/A')})<br>"
        f"Poverty Rate: {fmt_val(row['poverty_rate_pct'], '%')}<br>"
        f"Single Mother HH: {fmt_val(row['single_mother_pct'], '%')}<br>"
        f"Unemployment: {fmt_val(row['unemployment_rate_pct'], '%')}<br>"
        f"Uninsured: {fmt_val(row['uninsured_rate_pct'], '%')}<br>"
        f"MH Events: {fmt_val(row['mh_events_per_100k'], 'per 100k')} per 100k"
    )

master["hover_text"] = master.apply(build_hover, axis=1)

# ─── 5. BUILD PLOTLY FIGURE ───────────────────────────────────────────────────
fig = go.Figure()

# Choropleth layers — one per metric, toggle via JS
for i, layer in enumerate(LAYERS):
    col_data = master[layer["key"]].fillna(0)
    # go.Choropleth with custom GeoJSON renders purely in SVG/WebGL —
    # no external tile server needed, works from local file:// URLs.
    fig.add_trace(go.Choropleth(
        geojson=indiana_geojson,
        locations=master["county_fips"],
        z=col_data,
        featureidkey="id",
        colorscale=layer["color"],
        zmin=col_data.min(),
        zmax=col_data.max(),
        marker_opacity=0.80,
        marker_line_width=0.5,
        marker_line_color="white",
        colorbar=dict(
            title=dict(text=layer["unit"], font=dict(size=10)),
            thickness=12, len=0.60, x=0.0, xanchor="left",
            tickfont=dict(size=9),
            bgcolor="rgba(255,255,255,0.8)",
            borderwidth=0,
        ),
        text=master["hover_text"],
        hovertemplate="%{text}<extra></extra>",
        visible=(i == 0),
        name=layer["label"],
        showscale=True,
    ))

# OTP facility pins — go.Scattergeo needs no tile server
fig.add_trace(go.Scattergeo(
    lat=otp["lat"],
    lon=otp["lon"],
    mode="markers",
    marker=dict(size=9, color="#2563EB", opacity=0.9,
                line=dict(width=1.5, color="white")),
    text=otp["facility_name"] + "<br>" + otp["city"].fillna(""),
    hovertemplate="<b>OTP Facility</b><br>%{text}<extra></extra>",
    name="OTP Facilities (26)",
    visible=True,
    showlegend=False,
))

# Dove House existing location pins
fig.add_trace(go.Scattergeo(
    lat=DOVE_LOCS["lat"],
    lon=DOVE_LOCS["lon"],
    mode="markers",
    marker=dict(size=16, color="#C41230", opacity=1.0, symbol="star",
                line=dict(width=2, color="white")),
    text=DOVE_LOCS["label"],
    hovertemplate="<b>%{text}</b><br>Existing Dove House Center<extra></extra>",
    name="Existing Dove House",
    visible=True,
    showlegend=False,
))

fig.update_layout(
    geo=dict(
        # No scope — use explicit bounds to zoom into Indiana
        projection_type="mercator",
        showland=True,    landcolor="#EDE9E0",
        showlakes=True,   lakecolor="#BFD7EA",
        showframe=False,
        showcoastlines=True, coastlinecolor="#CCCCCC",
        showcountries=False,
        showsubunits=True, subunitcolor="#DDDDDD",
        lonaxis=dict(range=[-88.6, -84.6]),
        lataxis=dict(range=[37.6, 42.1]),
        bgcolor="#F8F5F2",
    ),
    margin=dict(t=0, b=0, l=0, r=0),
    showlegend=False,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    height=620,
)

# ─── 6. GENERATE MAP DIV ──────────────────────────────────────────────────────
map_div_html = fig.to_html(
    include_plotlyjs=False,
    full_html=False,
    div_id="main-map",
    config=dict(
        displayModeBar=True,
        displaylogo=False,
        modeBarButtonsToRemove=["select2d", "lasso2d"],
        toImageButtonOptions=dict(format="png", filename="dove_house_map", height=900, width=1400, scale=2),
    ),
)

# ─── 7. TOP-10 RANKING HTML ───────────────────────────────────────────────────
top10 = master.sort_values("county_rank").head(10)
max_score = master["composite_need_score"].max()

ranking_rows = ""
for _, row in top10.iterrows():
    rank = int(row["county_rank"])
    badge_cls = "top3" if rank <= 3 else ""
    cname = row["county_name"].replace(" County", "")
    score = row["composite_need_score"]
    bar_w = int(score / max_score * 80)
    dove_tag = " ★" if row["is_dove_house"] else ""
    ranking_rows += (
        f'<tr><td><span class="rank-badge {badge_cls}">{rank}</span></td>'
        f'<td>{cname}{dove_tag}</td>'
        f'<td><span style="font-weight:600;color:#C41230">{score:.1f}</span>'
        f'<div style="height:4px;width:{bar_w}px;background:#FCA5A5;border-radius:2px;margin-top:2px"></div></td>'
        f'</tr>'
    )

# ─── 8. LAYER BUTTONS HTML ────────────────────────────────────────────────────
buttons_html = ""
for i, layer in enumerate(LAYERS):
    active_cls = "active" if i == 0 else ""
    buttons_html += (
        f'<button class="layer-btn {active_cls}" onclick="switchLayer({i})">'
        f'{layer["label"]}</button>'
    )

# ─── 9. JAVASCRIPT DATA ───────────────────────────────────────────────────────
layer_labels = json.dumps([l["label"] for l in LAYERS])
layer_descs  = json.dumps([l["desc"]  for l in LAYERS])

first_label = LAYERS[0]["label"]
first_desc  = LAYERS[0]["desc"]

# ─── 10. BUILD FULL HTML PAGE ─────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dove House — Indiana Site Selection Dashboard</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #F8F5F2; color: #1A1A2E; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }}

    /* ── Header ── */
    .header {{
      background: #1A1A2E;
      padding: 10px 24px;
      display: flex;
      align-items: center;
      gap: 16px;
      flex-shrink: 0;
    }}
    .logo-block {{ line-height: 1; }}
    .logo-name {{ color: #C41230; font-size: 20px; font-weight: 900; letter-spacing: 2px; }}
    .logo-sub  {{ color: #C41230; font-size: 8px; letter-spacing: 3px; margin-top: 1px; }}
    .divider   {{ width: 1px; height: 38px; background: #374151; }}
    .header-text h1 {{ color: white; font-size: 15px; font-weight: 600; }}
    .header-text p  {{ color: #9CA3AF; font-size: 11px; margin-top: 2px; }}
    .header-badge {{
      margin-left: auto;
      background: rgba(196,18,48,0.15);
      border: 1px solid rgba(196,18,48,0.4);
      color: #FCA5A5;
      font-size: 11px;
      padding: 4px 12px;
      border-radius: 20px;
    }}

    /* ── Controls bar ── */
    .controls-bar {{
      background: white;
      padding: 10px 20px;
      display: flex;
      align-items: center;
      gap: 6px;
      border-bottom: 2px solid #E5E7EB;
      flex-shrink: 0;
      flex-wrap: wrap;
    }}
    .ctrl-label {{
      font-size: 10px;
      color: #9CA3AF;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      font-weight: 700;
      margin-right: 6px;
    }}
    .layer-btn {{
      padding: 6px 14px;
      border-radius: 6px;
      border: 1.5px solid #E5E7EB;
      background: white;
      color: #4B5563;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
      white-space: nowrap;
    }}
    .layer-btn:hover {{ background: #F9FAFB; border-color: #9CA3AF; color: #111; }}
    .layer-btn.active {{ background: #C41230; color: white; border-color: #C41230; font-weight: 600; }}

    /* ── Body ── */
    .body-area {{
      display: flex;
      flex: 1;
      overflow: hidden;
    }}

    /* ── Map area ── */
    .map-area {{
      flex: 1;
      position: relative;
      overflow: hidden;
    }}
    #main-map {{ width: 100%; height: 100%; }}
    .map-overlay {{
      position: absolute;
      top: 14px;
      left: 14px;
      background: rgba(255,255,255,0.95);
      border-radius: 10px;
      padding: 10px 16px;
      z-index: 1000;
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
      max-width: 440px;
      pointer-events: none;
    }}
    .map-overlay h2 {{ font-size: 14px; font-weight: 700; color: #C41230; margin-bottom: 4px; }}
    .map-overlay p  {{ font-size: 11px; color: #6B7280; line-height: 1.5; }}

    .map-legend {{
      position: absolute;
      bottom: 30px;
      left: 14px;
      background: rgba(255,255,255,0.93);
      border-radius: 8px;
      padding: 10px 14px;
      z-index: 1000;
      box-shadow: 0 2px 8px rgba(0,0,0,0.10);
      pointer-events: none;
    }}
    .map-legend h4 {{ font-size: 10px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin-bottom: 8px; }}
    .legend-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 11px; color: #374151; }}
    .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; border: 2px solid white; box-shadow: 0 0 0 1px currentColor; }}

    /* ── Sidebar ── */
    .sidebar {{
      width: 270px;
      background: white;
      border-left: 1px solid #E5E7EB;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      flex-shrink: 0;
    }}
    .sidebar-section {{ padding: 14px 16px; border-bottom: 1px solid #F3F4F6; }}
    .sidebar-section h3 {{
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: #9CA3AF;
      font-weight: 700;
      margin-bottom: 10px;
    }}

    /* Rankings */
    .rank-table {{ width: 100%; border-collapse: collapse; }}
    .rank-table th {{
      font-size: 10px; color: #9CA3AF; text-align: left;
      padding: 3px 6px; border-bottom: 1px solid #E5E7EB;
      font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
    }}
    .rank-table td {{ font-size: 12px; padding: 5px 6px; border-bottom: 1px solid #F9FAFB; vertical-align: middle; }}
    .rank-table tr:hover td {{ background: #FFF5F5; }}
    .rank-badge {{
      display: inline-flex; align-items: center; justify-content: center;
      width: 20px; height: 20px; border-radius: 50%;
      background: #FEE2E2; color: #C41230;
      font-size: 10px; font-weight: 800;
    }}
    .rank-badge.top3 {{ background: #C41230; color: white; }}

    /* Score weights */
    .weight-row {{ display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 11px; }}
    .weight-row span:first-child {{ color: #4B5563; }}
    .weight-pct {{ font-weight: 700; color: #C41230; font-size: 11px; }}
    .weight-bar {{ height: 3px; border-radius: 2px; background: #FCA5A5; margin-top: 2px; }}

    /* Footer */
    .footer {{
      background: #F9FAFB;
      border-top: 1px solid #E5E7EB;
      padding: 5px 20px;
      font-size: 10px;
      color: #9CA3AF;
      flex-shrink: 0;
    }}
  </style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="logo-block">
    <div class="logo-name">DOVE</div>
    <div class="logo-sub">RECOVERY HOUSE</div>
  </div>
  <div class="divider"></div>
  <div class="header-text">
    <h1>Indiana Site Selection Dashboard</h1>
    <p>Identifying the ideal county for the next Dove House center — data-driven, geospatial analysis</p>
  </div>
  <div class="header-badge">92 Indiana Counties Analyzed</div>
</div>

<!-- Layer toggle buttons -->
<div class="controls-bar">
  <span class="ctrl-label">View By</span>
  {buttons_html}
</div>

<!-- Main body -->
<div class="body-area">

  <!-- Map -->
  <div class="map-area">
    <!-- Title overlay -->
    <div class="map-overlay">
      <h2 id="layer-title">{first_label}</h2>
      <p id="layer-desc">{first_desc}</p>
    </div>
    <!-- Map legend overlay -->
    <div class="map-legend">
      <h4>Map Layers</h4>
      <div class="legend-row">
        <div class="legend-dot" style="background:#2563EB;color:#2563EB"></div>
        OTP Facilities (26)
      </div>
      <div class="legend-row">
        <span style="font-size:16px;color:#C41230;line-height:1">★</span>
        Dove House Centers (3)
      </div>
    </div>
    <!-- Plotly map -->
    {map_div_html}
  </div>

  <!-- Sidebar -->
  <div class="sidebar">

    <div class="sidebar-section">
      <h3>Top 10 Priority Counties</h3>
      <table class="rank-table">
        <thead>
          <tr><th>#</th><th>County</th><th>Score</th></tr>
        </thead>
        <tbody>
          {ranking_rows}
        </tbody>
      </table>
    </div>

    <div class="sidebar-section">
      <h3>Composite Score Weights</h3>
      <div class="weight-row">
        <span>Overdose Rate</span>
        <span class="weight-pct">25%</span>
      </div>
      <div class="weight-bar" style="width:80%"></div>
      <div style="height:6px"></div>
      <div class="weight-row">
        <span>OTP Access Gap</span>
        <span class="weight-pct">20%</span>
      </div>
      <div class="weight-bar" style="width:64%"></div>
      <div style="height:6px"></div>
      <div class="weight-row">
        <span>Women's Poverty</span>
        <span class="weight-pct">20%</span>
      </div>
      <div class="weight-bar" style="width:64%"></div>
      <div style="height:6px"></div>
      <div class="weight-row">
        <span>Single Mothers</span>
        <span class="weight-pct">15%</span>
      </div>
      <div class="weight-bar" style="width:48%"></div>
      <div style="height:6px"></div>
      <div class="weight-row">
        <span>Unemployment</span>
        <span class="weight-pct">10%</span>
      </div>
      <div class="weight-bar" style="width:32%"></div>
      <div style="height:6px"></div>
      <div class="weight-row">
        <span>Uninsured Rate</span>
        <span class="weight-pct">5%</span>
      </div>
      <div class="weight-bar" style="width:16%"></div>
      <div style="height:6px"></div>
      <div class="weight-row">
        <span>Mental Health Events</span>
        <span class="weight-pct">5%</span>
      </div>
      <div class="weight-bar" style="width:16%"></div>
    </div>

    <div class="sidebar-section">
      <h3>Data Sources</h3>
      <div style="font-size:10px;color:#9CA3AF;line-height:1.8">
        <div>CDC Drug Poisoning Mortality (2015)</div>
        <div>ACS 5-Year Estimates (2023)</div>
        <div>Indiana MPH Hub (2017–2024)</div>
        <div>SAMHSA OTP Locator (2025)</div>
        <div>TIGER/Line Shapefiles (2022)</div>
        <div>USDA ERS County Typology (2025)</div>
      </div>
    </div>

  </div><!-- /sidebar -->
</div><!-- /body-area -->

<div class="footer">
  ★ = Existing Dove House locations (Marion, Dubois &amp; Bartholomew counties) &nbsp;|&nbsp;
  Composite Need Score = weighted index of 7 county-level indicators across all 92 Indiana counties
</div>

<script>
const LAYER_LABELS = {layer_labels};
const LAYER_DESCS  = {layer_descs};
const N_LAYERS     = {N_LAYERS};

function switchLayer(idx) {{
  // Build visibility: show only the selected choropleth; always show pins
  const vis = [];
  for (let i = 0; i < N_LAYERS; i++) vis.push(i === idx);
  vis.push(true);  // OTP pins
  vis.push(true);  // Dove House pins

  Plotly.restyle('main-map', {{ visible: vis }});

  document.getElementById('layer-title').textContent = LAYER_LABELS[idx];
  document.getElementById('layer-desc').textContent  = LAYER_DESCS[idx];

  document.querySelectorAll('.layer-btn').forEach(function(btn, i) {{
    btn.classList.toggle('active', i === idx);
  }});
}}
</script>
</body>
</html>"""

out_path = OUT / "dove_house_consolidated_dashboard.html"
out_path.write_text(html, encoding="utf-8")
print(f"\nDashboard written to:\n  {out_path}")

# Also save master CSV
master_cols = [c for c in [
    "county_fips","county_name","county_rank","composite_need_score","is_dove_house",
    "overdose_rate_midpoint","rate_range","min_drive_time_min","avg_drive_time_min",
    "otp_access_tier","poverty_rate_pct","median_hh_income","single_mother_pct",
    "unemployment_rate_pct","uninsured_rate_pct","rent_burden_30pct_rate",
    "mh_events_per_100k","self_harm_per_100k",
    "n_overdose","n_drive_time","n_poverty","n_single_mom","n_unemployment","n_uninsured","n_mh_events",
] if c in master.columns]
master.sort_values("county_rank")[master_cols].to_csv(OUT / "00_master_county_metrics.csv", index=False)
print(f"Master metrics: {OUT / '00_master_county_metrics.csv'}")
print("Done.")
