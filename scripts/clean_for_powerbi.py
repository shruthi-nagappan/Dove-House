"""
clean_for_powerbi.py
Dove House — produce Power-BI-ready CSVs from the data_by_criteria repo.

Run from anywhere:
    python "c:/Users/mrnai/Downloads/Dove House/data_by_criteria/scripts/clean_for_powerbi.py"

Outputs go to:
    data_by_criteria/powerbi_ready/
"""

import pandas as pd
from pathlib import Path

ROOT = Path("c:/Users/mrnai/Downloads/Dove House/data_by_criteria")
DBC = ROOT / "data_by_criteria"
OUT = ROOT / "powerbi_ready"
OUT.mkdir(exist_ok=True)

print("=" * 60)
print("Dove House — Power BI Data Prep")
print("=" * 60)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def make_fips(county_int_series):
    """Convert county integer (1, 3, …) to 5-digit Indiana FIPS (18001, …)."""
    return "18" + county_int_series.astype(str).str.zfill(3)


def normalize_0_100(series):
    """Min-max scale to [0, 100]. Higher = more need."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([50.0] * len(series), index=series.index)
    return ((series - mn) / (mx - mn) * 100).round(2)


def drive_time_midpoint(label):
    mapping = {"0-15": 7.5, "15-30": 22.5, "30-45": 37.5, "45-60": 52.5, "60-90": 75.0}
    return mapping.get(str(label), None)


def range_to_midpoint(r):
    """Convert '10.1-12' CDC rate range to its midpoint float."""
    try:
        parts = str(r).split("-")
        return (float(parts[0]) + float(parts[1])) / 2
    except Exception:
        return None


# ─── 1. COUNTY BASE (92 Indiana counties) ─────────────────────────────────────
print("\n[1/7] Building county base & FIPS lookup...")

female_pop = pd.read_csv(
    DBC / "01_economic_housing_stress/census_acs/acs_in_counties_population_female.csv"
)
female_pop["county_fips"] = make_fips(female_pop["county"])
female_pop["county_name"] = female_pop["NAME"].str.replace(", Indiana", "", regex=False)
female_pop = female_pop.rename(columns={"B01001_001E": "total_pop", "B01001_026E": "female_pop"})
female_pop["female_share_pct"] = (female_pop["female_pop"] / female_pop["total_pop"] * 100).round(1)
female_pop["female_share"] = (female_pop["female_pop"] / female_pop["total_pop"]).round(4)

county_base = female_pop[
    ["county_fips", "county_name", "total_pop", "female_pop", "female_share_pct", "female_share"]
].copy()

# Build lookup: short county name (upper, no "County") → FIPS
county_base["_short"] = (
    county_base["county_name"]
    .str.replace(" County", "", regex=False)
    .str.upper()
    .str.strip()
)
fips_lookup = county_base.set_index("_short")["county_fips"].to_dict()

county_base.drop(columns=["_short"]).to_csv(OUT / "01_county_base.csv", index=False)
print(f"  → 01_county_base.csv  ({len(county_base)} rows)")


# ─── 2. SOCIOECONOMIC METRICS ─────────────────────────────────────────────────
print("\n[2/7] Building socioeconomic metrics...")

# Income & poverty (B17001, B19013)
income_pov = pd.read_csv(
    DBC / "01_economic_housing_stress/census_acs/acs_in_counties_income_poverty.csv"
)
income_pov["county_fips"] = make_fips(income_pov["county"])
income_pov["poverty_rate_pct"] = (
    income_pov["B17001_002E"] / income_pov["B17001_001E"] * 100
).round(1)
income_pov = income_pov.rename(
    columns={"B19013_001E": "median_hh_income", "B17001_002E": "poverty_count"}
)[["county_fips", "median_hh_income", "poverty_count", "poverty_rate_pct"]]

# Unemployment & insurance (DP03)
dp03 = pd.read_csv(
    DBC / "01_economic_housing_stress/acs_extended/acs_in_counties_dp03_insurance_unemployment_2023.csv"
)
dp03["county_fips"] = make_fips(dp03["county"])
dp03 = dp03.rename(columns={
    "DP03_0009PE": "unemployment_rate_pct",
    "DP03_0099PE": "uninsured_rate_pct",
    "DP03_0004PE": "employment_rate_pct",
    "DP03_0129PE": "medicaid_rate_pct",
})[["county_fips", "unemployment_rate_pct", "uninsured_rate_pct",
    "employment_rate_pct", "medicaid_rate_pct"]]

# Households & single mothers (B11002, B11005)
hh = pd.read_csv(
    DBC / "01_economic_housing_stress/acs_extended/acs_in_counties_b11002_b11005_households_2023.csv"
)
hh["county_fips"] = make_fips(hh["county"])
hh["single_mother_hh_with_kids"] = hh["B11005_007E"]
hh["hh_with_kids_total"] = hh["B11005_001E"]
hh["single_mother_pct"] = (hh["B11005_007E"] / hh["B11005_001E"] * 100).round(1)
hh["female_hh_no_spouse_pop"] = hh["B11002_012E"]
hh = hh[[
    "county_fips", "single_mother_hh_with_kids", "hh_with_kids_total",
    "single_mother_pct", "female_hh_no_spouse_pop"
]]

# Rent burden — 30%+ means sum of buckets 007-010 / 001 (B25070)
rent = pd.read_csv(
    DBC / "01_economic_housing_stress/census_acs/acs_in_counties_gross_rent_as_pct_income_B25070.csv"
)
rent["county_fips"] = make_fips(rent["county"])
rent["rent_burdened_count"] = (
    rent["B25070_007E"] + rent["B25070_008E"] + rent["B25070_009E"] + rent["B25070_010E"]
)
rent["total_renters"] = rent["B25070_001E"]
rent["rent_burden_30pct_rate"] = (rent["rent_burdened_count"] / rent["total_renters"] * 100).round(1)
rent = rent[["county_fips", "total_renters", "rent_burdened_count", "rent_burden_30pct_rate"]]

# Merge everything
socio = (
    county_base[["county_fips", "county_name", "total_pop", "female_pop", "female_share_pct"]]
    .merge(income_pov, on="county_fips")
    .merge(dp03, on="county_fips")
    .merge(hh, on="county_fips")
    .merge(rent, on="county_fips")
)
socio.to_csv(OUT / "02_county_socioeconomic.csv", index=False)
print(f"  → 02_county_socioeconomic.csv  ({len(socio)} rows, {len(socio.columns)} cols)")


# ─── 3. OVERDOSE MORTALITY (CDC) ──────────────────────────────────────────────
print("\n[3/7] Building overdose mortality data...")

mart = pd.read_csv(ROOT / "datawarehouse/mart_county_overdose_context.csv",
                   dtype={"county_fips": str})
mart["overdose_rate_midpoint"] = mart["rate_range"].apply(range_to_midpoint)

# Latest snapshot (year 2015 in CDC county data)
latest_year = mart["cdc_year"].max()
latest_od = mart[mart["cdc_year"] == latest_year].copy()
latest_od = latest_od.rename(columns={"cdc_year": "cdc_data_year"})[
    ["county_fips", "county_name", "cdc_data_year", "rate_range",
     "overdose_rate_midpoint", "acs_female_pop"]
]
latest_od.to_csv(OUT / "03a_county_overdose_latest.csv", index=False)
print(f"  → 03a_county_overdose_latest.csv  ({len(latest_od)} rows, year={latest_year})")

# Full time-series for trend chart
full_od = mart.rename(columns={"rate_midpoint": "overdose_rate_midpoint"})[
    ["county_fips", "county_name", "cdc_year", "rate_range", "overdose_rate_midpoint"]
]
full_od.to_csv(OUT / "03b_county_overdose_timeseries.csv", index=False)
print(f"  → 03b_county_overdose_timeseries.csv  ({len(full_od)} rows, years {mart['cdc_year'].min()}–{mart['cdc_year'].max()})")


# ─── 4. OTP LOCATIONS (point data) ────────────────────────────────────────────
print("\n[4/7] Building OTP location points...")

otp = pd.read_csv(
    DBC / "02_access_health_social_services/opioid_treatment_program_locations/otp_otp_locations_20250922.csv"
)
otp.columns = [c.lower() for c in otp.columns]
otp["county_fips"] = make_fips(otp["location_county"])
# Clean up
otp = otp.rename(columns={
    "location_id": "otp_id", "location_zip": "zip", "location_city": "city",
    "location_street": "street", "location_county": "county_fips_suffix",
    "name": "facility_name", "phone": "phone", "latitude": "lat", "longitude": "lon"
})
otp.to_csv(OUT / "04_otp_locations.csv", index=False)
print(f"  → 04_otp_locations.csv  ({len(otp)} rows)")


# ─── 5. OTP DRIVE TIME BY COUNTY ──────────────────────────────────────────────
print("\n[5/7] Building OTP drive time by county...")

drive = pd.read_csv(
    DBC / "02_access_health_social_services/mph_hub/opioid-treatment-program-drive-time/Opioid_Treatment_Program_Drive_Time.csv"
)
drive["drive_time_midpoint_min"] = drive["OTP_DRIVE_TIME_IN_MINUTES"].apply(drive_time_midpoint)

# Aggregate to county level (min = best-served ZCTA; avg = central tendency)
county_drive = (
    drive.groupby("COUNTY")["drive_time_midpoint_min"]
    .agg(
        min_drive_time_min="min",
        avg_drive_time_min="mean",
        max_drive_time_min="max",
        zcta_count="count",
    )
    .reset_index()
    .rename(columns={"COUNTY": "county_short"})
)
county_drive["avg_drive_time_min"] = county_drive["avg_drive_time_min"].round(1)

# Map county name → FIPS (normalize punctuation for e.g. "St. Joseph")
fips_lookup_nopunct_drive = {k.replace(".", ""): v for k, v in fips_lookup.items()}
county_drive["county_short_upper"] = county_drive["county_short"].str.upper().str.strip().str.replace(".", "", regex=False)
county_drive["county_fips"] = county_drive["county_short_upper"].map(fips_lookup_nopunct_drive)

unmatched = county_drive[county_drive["county_fips"].isna()]["county_short"].tolist()
if unmatched:
    print(f"  ! Drive time FIPS unmatched ({len(unmatched)}): {unmatched}")

# Access tier label for Power BI slicer
def access_tier(v):
    if v <= 15:   return "0–15 min"
    elif v <= 30: return "15–30 min"
    elif v <= 45: return "30–45 min"
    elif v <= 60: return "45–60 min"
    else:         return "60+ min"

county_drive["otp_access_tier"] = county_drive["min_drive_time_min"].apply(access_tier)
county_drive = county_drive.merge(
    county_base[["county_fips", "county_name"]], on="county_fips", how="left"
)
county_drive = county_drive[[
    "county_fips", "county_name", "county_short", "zcta_count",
    "min_drive_time_min", "avg_drive_time_min", "max_drive_time_min", "otp_access_tier"
]]
county_drive.to_csv(OUT / "05_county_otp_drive_time.csv", index=False)
print(f"  → 05_county_otp_drive_time.csv  ({len(county_drive)} rows)")


# ─── 6. MENTAL HEALTH EVENTS BY COUNTY ────────────────────────────────────────
print("\n[6/7] Building mental health events by county...")

mh = pd.read_csv(
    DBC / "02_access_health_social_services/mph_hub/mental-health-related-ems-and-ed-events-by-county/Mental_Health_Related_EMS_and_ED_Events_by_County.csv"
)

# Map county name (ALL CAPS) → FIPS
# Normalize: remove periods so "ST JOSEPH" matches "ST. JOSEPH"
def normalize_county(name):
    return str(name).upper().strip().replace(".", "")

# Build a period-stripped version of the fips_lookup
fips_lookup_nopunct = {k.replace(".", ""): v for k, v in fips_lookup.items()}
mh["county_fips"] = mh["EVENT_COUNTY"].apply(normalize_county).map(fips_lookup_nopunct)

unmatched_mh = mh[mh["county_fips"].isna()]["EVENT_COUNTY"].unique().tolist()
if unmatched_mh:
    print(f"  ! MH county FIPS unmatched: {unmatched_mh[:10]}")

# Aggregate across age groups → county + year totals
mh_county = (
    mh.groupby(["county_fips", "EVENT_COUNTY", "EVENT_YR"])[
        ["NONPHYS_MENTAL_HEALTH_FLG_CNT", "SUICIDAL_AND_SELF_HARM_FLG_CNT",
         "HOMICIDAL_AND_HARM_TO_OTHERS_FLG_FLG_CNT"]
    ]
    .sum()
    .reset_index()
    .rename(columns={
        "EVENT_COUNTY": "county_short_raw",
        "EVENT_YR": "year",
        "NONPHYS_MENTAL_HEALTH_FLG_CNT": "mh_events_total",
        "SUICIDAL_AND_SELF_HARM_FLG_CNT": "self_harm_events",
        "HOMICIDAL_AND_HARM_TO_OTHERS_FLG_FLG_CNT": "homicide_harm_events",
    })
)

# Join population for per-100k rates
mh_county = mh_county.merge(
    county_base[["county_fips", "county_name", "total_pop"]], on="county_fips", how="left"
)
mh_county["mh_events_per_100k"] = (
    mh_county["mh_events_total"] / mh_county["total_pop"] * 100_000
).round(1)
mh_county["self_harm_per_100k"] = (
    mh_county["self_harm_events"] / mh_county["total_pop"] * 100_000
).round(1)

mh_county.to_csv(OUT / "06_county_mental_health_events.csv", index=False)
print(f"  → 06_county_mental_health_events.csv  ({len(mh_county)} rows, years {mh_county['year'].min()}–{mh_county['year'].max()})")


# ─── 7. COMPOSITE NEED SCORE ──────────────────────────────────────────────────
print("\n[7/7] Computing composite need score...")

# Use average across all years — avoids partial-year 2024 data showing 0 for small counties
mh_latest = (
    mh_county.groupby("county_fips")[["mh_events_per_100k", "self_harm_per_100k"]]
    .mean()
    .round(1)
    .reset_index()
)

score_df = (
    county_base[["county_fips", "county_name", "female_pop", "total_pop", "female_share"]]
    .merge(socio[["county_fips", "poverty_rate_pct", "unemployment_rate_pct",
                   "uninsured_rate_pct", "single_mother_pct", "rent_burden_30pct_rate"]],
           on="county_fips")
    .merge(latest_od[["county_fips", "overdose_rate_midpoint", "rate_range"]],
           on="county_fips", how="left")
    .merge(county_drive[["county_fips", "min_drive_time_min", "otp_access_tier"]],
           on="county_fips", how="left")
    .merge(mh_latest, on="county_fips", how="left")
)

# Fill missing overdose midpoints with median
od_median = score_df["overdose_rate_midpoint"].median()
score_df["overdose_rate_midpoint"] = score_df["overdose_rate_midpoint"].fillna(od_median)

# Fill missing drive times with worst case (75 = 60-90 min midpoint)
score_df["min_drive_time_min"] = score_df["min_drive_time_min"].fillna(75)

# Fill missing MH events with 0
score_df["mh_events_per_100k"] = score_df["mh_events_per_100k"].fillna(0)

# Gender-adjust gender-neutral metrics by female population share
# Downweights counties with prison-heavy male populations (e.g. Perry 0.45, Sullivan 0.46)
for col in ["overdose_rate_midpoint", "mh_events_per_100k",
            "poverty_rate_pct", "unemployment_rate_pct", "uninsured_rate_pct"]:
    score_df[col] = (score_df[col] * score_df["female_share"]).round(2)

# Normalize each component → 0-100 (higher = more need)
score_df["n_overdose"]     = normalize_0_100(score_df["overdose_rate_midpoint"])
score_df["n_drive_time"]   = normalize_0_100(score_df["min_drive_time_min"])
score_df["n_poverty"]      = normalize_0_100(score_df["poverty_rate_pct"])
score_df["n_single_mom"]   = normalize_0_100(score_df["single_mother_pct"])
score_df["n_unemployment"] = normalize_0_100(score_df["unemployment_rate_pct"])
score_df["n_uninsured"]    = normalize_0_100(score_df["uninsured_rate_pct"])
score_df["n_mh_events"]    = normalize_0_100(score_df["mh_events_per_100k"])

# Weighted composite — weights sum to 1.0
weights = {
    "n_overdose":     0.25,
    "n_drive_time":   0.20,
    "n_poverty":      0.20,
    "n_single_mom":   0.15,
    "n_unemployment": 0.10,
    "n_uninsured":    0.05,
    "n_mh_events":    0.05,
}
score_df["composite_need_score"] = sum(
    score_df[col] * w for col, w in weights.items()
).round(1)
score_df["county_rank"] = (
    score_df["composite_need_score"].rank(ascending=False, method="min").astype(int)
)

score_df = score_df.sort_values("county_rank")

# Output columns
out_cols = [
    "county_fips", "county_name", "female_pop", "total_pop", "female_share",
    # Raw metrics (gender-adjusted where applicable)
    "overdose_rate_midpoint", "rate_range", "min_drive_time_min", "otp_access_tier",
    "poverty_rate_pct", "single_mother_pct", "unemployment_rate_pct",
    "uninsured_rate_pct", "mh_events_per_100k",
    # Normalized components
    "n_overdose", "n_drive_time", "n_poverty", "n_single_mom",
    "n_unemployment", "n_uninsured", "n_mh_events",
    # Final score
    "composite_need_score", "county_rank",
]
score_df[out_cols].to_csv(OUT / "07_county_composite_score.csv", index=False)
print(f"  → 07_county_composite_score.csv  ({len(score_df)} rows)")

print("\n── TOP 10 COUNTIES BY NEED SCORE ──────────────────────────────")
print(
    score_df[["county_rank", "county_name", "composite_need_score",
              "overdose_rate_midpoint", "min_drive_time_min", "poverty_rate_pct"]]
    .head(10)
    .to_string(index=False)
)

print("\n── BOTTOM 5 COUNTIES (lowest need / best served) ───────────────")
print(
    score_df[["county_rank", "county_name", "composite_need_score"]]
    .tail(5)
    .to_string(index=False)
)

print("\n" + "=" * 60)
print(f"Done. All CSVs written to:\n  {OUT}")
print("=" * 60)
