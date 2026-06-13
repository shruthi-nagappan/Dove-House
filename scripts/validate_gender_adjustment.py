"""
validate_gender_adjustment.py
Dove House — Data Quality & Gender-Adjustment Validation

Checks:
  1. Coverage        — 92 counties, no nulls, no duplicates
  2. Female share    — plausible range, known counties correct
  3. Adjustment      — adjusted values = raw × female_share (cross-check against intermediate CSVs)
  4. Non-adjusted    — drive time and single_mother_pct unchanged
  5. Score integrity — composite 0–100, ranks 1–92, no ties/gaps
  6. Ranking shift   — prison counties dropped, high-female counties held/rose
  7. Dove House      — Marion, Dubois, Bartholomew present

Run from anywhere:
    python "c:/Users/mrnai/Downloads/Dove House/data_by_criteria/scripts/validate_gender_adjustment.py"
"""

import pandas as pd
from pathlib import Path

ROOT = Path("c:/Users/mrnai/Downloads/Dove House/data_by_criteria")
OUT  = ROOT / "powerbi_ready"

PASS = "  [PASS]"
FAIL = "  [FAIL]"
INFO = "  [INFO]"

errors = []

def check(label, condition, detail=""):
    if condition:
        print(f"{PASS} {label}")
    else:
        print(f"{FAIL} {label}" + (f" — {detail}" if detail else ""))
        errors.append(label)

print("=" * 65)
print("Dove House — Gender Adjustment Validation")
print("=" * 65)

# ── Load files ─────────────────────────────────────────────────────
master  = pd.read_csv(OUT / "00_master_county_metrics.csv", dtype={"county_fips": str})
score7  = pd.read_csv(OUT / "07_county_composite_score.csv", dtype={"county_fips": str})
raw_od  = pd.read_csv(OUT / "03a_county_overdose_latest.csv", dtype={"county_fips": str})
raw_soc = pd.read_csv(OUT / "02_county_socioeconomic.csv", dtype={"county_fips": str})
raw_drv = pd.read_csv(OUT / "05_county_otp_drive_time.csv", dtype={"county_fips": str})
base    = pd.read_csv(OUT / "01_county_base.csv", dtype={"county_fips": str})

print("\n── TEST 1: Coverage ──────────────────────────────────────────")
check("Master CSV has 92 counties", len(master) == 92, f"got {len(master)}")
check("No duplicate county_fips", master["county_fips"].nunique() == 92)
check("female_share column present in master", "female_share" in master.columns)

key_cols = ["county_fips", "county_name", "composite_need_score", "county_rank",
            "female_share", "overdose_rate_midpoint", "poverty_rate_pct",
            "unemployment_rate_pct", "uninsured_rate_pct", "mh_events_per_100k"]
for col in key_cols:
    nulls = master[col].isna().sum()
    check(f"No nulls in '{col}'", nulls == 0, f"{nulls} nulls found")

print("\n── TEST 2: Female Share Plausibility ─────────────────────────")
fs = score7.set_index("county_fips")["female_share"]

check("All female_share between 0.40 and 0.60",
      fs.between(0.40, 0.60).all(),
      f"out-of-range: {fs[~fs.between(0.40, 0.60)].to_dict()}")

known = {
    "18123": ("Perry County",    0.454, 0.005),
    "18153": ("Sullivan County", 0.456, 0.005),
    "18053": ("Grant County",    0.519, 0.005),
    "18097": ("Marion County",   0.515, 0.005),
}
for fips, (name, expected, tol) in known.items():
    actual = fs.get(fips, None)
    if actual is None:
        check(f"{name} ({fips}) female_share ≈ {expected}", False, "county not found")
    else:
        ok = abs(actual - expected) <= tol
        check(f"{name} female_share ≈ {expected} (actual {actual:.4f})", ok,
              f"differs by {abs(actual - expected):.4f}")

print(f"\n{INFO} Female share range: {fs.min():.4f} – {fs.max():.4f}")
print(f"{INFO} Bottom 5 (prison-heavy):")
for fips, val in fs.nsmallest(5).items():
    name = score7.set_index("county_fips").loc[fips, "county_name"]
    print(f"       {name:30s} {val:.4f}")
print(f"{INFO} Top 5 (female-heavy):")
for fips, val in fs.nlargest(5).items():
    name = score7.set_index("county_fips").loc[fips, "county_name"]
    print(f"       {name:30s} {val:.4f}")

print("\n── TEST 3: Adjustment Correctness ────────────────────────────")
# Intermediate CSVs (03a, 02) were written BEFORE the adjustment block
# so they hold the original unadjusted values.
# Expected: adjusted_value ≈ raw_value × female_share

merged_od = score7.merge(
    raw_od[["county_fips", "overdose_rate_midpoint"]].rename(
        columns={"overdose_rate_midpoint": "raw_od"}),
    on="county_fips", how="left"
).merge(score7[["county_fips", "female_share"]], on="county_fips", how="left")

merged_od["expected_adj_od"] = (merged_od["raw_od"] * merged_od["female_share_x"]).round(2)
merged_od["actual_adj_od"]   = merged_od["overdose_rate_midpoint"]
# Exclude counties where CDC suppressed overdose data (filled with median, not raw × female_share)
od_check = merged_od.dropna(subset=["raw_od"])
od_diff = (od_check["expected_adj_od"] - od_check["actual_adj_od"]).abs()
suppressed = len(merged_od) - len(od_check)
print(f"{INFO} {suppressed} counties with suppressed CDC overdose data excluded from this check")
check(f"Overdose rate = raw × female_share ({len(od_check)} non-suppressed counties, tol 0.01)",
      (od_diff <= 0.01).all(),
      f"max diff {od_diff.max():.4f} at {od_check.loc[od_diff.idxmax(), 'county_fips']}")

merged_soc = score7.merge(
    raw_soc[["county_fips", "poverty_rate_pct", "unemployment_rate_pct", "uninsured_rate_pct"]],
    on="county_fips", how="left", suffixes=("_adj", "_raw")
)
for raw_col, adj_col in [
    ("poverty_rate_pct_raw",      "poverty_rate_pct_adj"),
    ("unemployment_rate_pct_raw", "unemployment_rate_pct_adj"),
    ("uninsured_rate_pct_raw",    "uninsured_rate_pct_adj"),
]:
    merged_soc["expected"] = (merged_soc[raw_col] * merged_soc["female_share"]).round(2)
    diff = (merged_soc["expected"] - merged_soc[adj_col]).abs()
    metric = raw_col.replace("_raw", "")
    check(f"{metric} = raw × female_share (tol 0.01)",
          (diff <= 0.01).all(),
          f"max diff {diff.max():.4f}")

print("\n── TEST 4: Non-Adjusted Columns Unchanged ────────────────────")
# drive time: score7 vs raw_drv (should be identical)
merged_drv = score7.merge(
    raw_drv[["county_fips", "min_drive_time_min"]].rename(
        columns={"min_drive_time_min": "raw_drive"}),
    on="county_fips", how="left"
)
drv_diff = (merged_drv["min_drive_time_min"] - merged_drv["raw_drive"]).abs()
check("min_drive_time_min NOT adjusted (matches raw_drv CSV)",
      (drv_diff <= 0.001).all(),
      f"max diff {drv_diff.max():.4f}")

# single_mother_pct: score7 vs raw_soc
merged_sm = score7.merge(
    raw_soc[["county_fips", "single_mother_pct"]].rename(
        columns={"single_mother_pct": "raw_sm"}),
    on="county_fips", how="left"
)
sm_diff = (merged_sm["single_mother_pct"] - merged_sm["raw_sm"]).abs()
check("single_mother_pct NOT adjusted (matches socio CSV)",
      (sm_diff <= 0.001).all(),
      f"max diff {sm_diff.max():.4f}")

print("\n── TEST 5: Score & Rank Integrity ────────────────────────────")
scores = master["composite_need_score"]
ranks  = master["county_rank"]

check("All composite scores between 0 and 100",
      scores.between(0, 100).all(),
      f"out-of-range: {scores[~scores.between(0, 100)].values}")

check("Rank min=1, max=92, count=92 (ties allowed with method=min)",
      ranks.min() == 1 and ranks.max() == 92 and len(ranks) == 92,
      f"min={ranks.min()}, max={ranks.max()}, count={len(ranks)}")
print(f"{INFO} Unique rank values: {ranks.nunique()} (< 92 means tied composite scores exist)")

check("Rank 1 county has highest composite score",
      master.loc[master["county_rank"] == 1, "composite_need_score"].values[0] ==
      master["composite_need_score"].max())

top1 = master.loc[master["county_rank"] == 1, "county_name"].values[0]
print(f"{INFO} Rank #1 county: {top1}")

print("\n── TEST 6: Ranking Shift (Prison County Effect) ──────────────")
# We expect Perry (0.45) and Sullivan (0.46) to rank lower (higher rank number)
# than they would have without adjustment.
# Simulate unadjusted scores for Perry and Sullivan to compare.
sim = score7.copy()

# Recover raw values by dividing out female_share
for col in ["overdose_rate_midpoint", "mh_events_per_100k",
            "poverty_rate_pct", "unemployment_rate_pct", "uninsured_rate_pct"]:
    sim[col + "_raw"] = (sim[col] / sim["female_share"]).round(4)

def normalize_0_100(s):
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series([50.0] * len(s), index=s.index)
    return ((s - mn) / (mx - mn) * 100).round(2)

sim["n_od_raw"]   = normalize_0_100(sim["overdose_rate_midpoint_raw"])
sim["n_pov_raw"]  = normalize_0_100(sim["poverty_rate_pct_raw"])
sim["n_unemp_raw"]= normalize_0_100(sim["unemployment_rate_pct_raw"])
sim["n_unins_raw"]= normalize_0_100(sim["uninsured_rate_pct_raw"])
sim["n_mh_raw"]   = normalize_0_100(sim["mh_events_per_100k_raw"])

weights = {"n_od_raw": 0.25, "n_drive_time": 0.20, "n_pov_raw": 0.20,
           "n_single_mom": 0.15, "n_unemp_raw": 0.10,
           "n_unins_raw": 0.05, "n_mh_raw": 0.05}
sim["unadj_score"] = sum(sim[c] * w for c, w in weights.items()).round(1)
sim["unadj_rank"]  = sim["unadj_score"].rank(ascending=False, method="min").astype(int)

# Compare adjusted ranks against pre-adjustment ranks from git HEAD
import subprocess, io
git_result = subprocess.run(
    ["git", "show", "HEAD:powerbi_ready/00_master_county_metrics.csv"],
    capture_output=True, text=True,
    cwd=str(ROOT)
)

if git_result.returncode != 0:
    print(f"{INFO} Could not read pre-adjustment data from git — skipping rank comparison")
else:
    old_master = pd.read_csv(io.StringIO(git_result.stdout), dtype={"county_fips": str})
    compare = {
        "18123": ("Perry County",    "prison-heavy → should DROP"),
        "18153": ("Sullivan County", "prison-heavy → should DROP"),
        "18103": ("Miami County",    "prison-heavy → should DROP"),
        "18053": ("Grant County",    "high female share → should RISE"),
        "18035": ("Delaware County", "high female share → should RISE"),
        "18097": ("Marion County",   "high female share → should RISE"),
    }
    print(f"\n  {'County':<25} {'Old Rank':>9} {'New Rank':>9} {'Change':>8} {'Result':>12}")
    print(f"  {'-'*25} {'-'*9} {'-'*9} {'-'*8} {'-'*12}")
    for fips, (name, expectation) in compare.items():
        old_row = old_master[old_master["county_fips"] == fips]
        new_row = score7[score7["county_fips"] == fips]
        if old_row.empty or new_row.empty:
            print(f"  {name:<25} {'N/A':>9} {'N/A':>9}")
            continue
        old_rank = int(old_row["county_rank"].values[0])
        new_rank = int(new_row["county_rank"].values[0])
        change = new_rank - old_rank
        direction = f"+{change} ↓" if change > 0 else (f"{change} ↑" if change < 0 else "0 =")
        result = "CORRECT" if (("DROP" in expectation and change > 0) or
                               ("RISE" in expectation and change < 0)) else "UNEXPECTED"
        print(f"  {name:<25} {old_rank:>9} {new_rank:>9} {direction:>8} {result:>12}")

    check("Perry County (prison) ranks lower after adjustment",
          score7[score7["county_fips"] == "18123"]["county_rank"].values[0] >
          old_master[old_master["county_fips"] == "18123"]["county_rank"].values[0])
    check("Sullivan County (prison) ranks lower after adjustment",
          score7[score7["county_fips"] == "18153"]["county_rank"].values[0] >
          old_master[old_master["county_fips"] == "18153"]["county_rank"].values[0])
    check("Grant County (high female share) ranks same or higher after adjustment",
          score7[score7["county_fips"] == "18053"]["county_rank"].values[0] <=
          old_master[old_master["county_fips"] == "18053"]["county_rank"].values[0])

print("\n── TEST 7: Dove House Counties Present ───────────────────────")
dove_fips = {"18097": "Marion", "18037": "Dubois", "18005": "Bartholomew"}
for fips, name in dove_fips.items():
    row = master[master["county_fips"] == fips]
    check(f"{name} County ({fips}) present in master",
          len(row) == 1)
    if len(row) == 1:
        print(f"{INFO}   {name}: composite={row['composite_need_score'].values[0]}, "
              f"rank={row['county_rank'].values[0]}, "
              f"female_share={row['female_share'].values[0]:.4f}")

print("\n── SUMMARY ───────────────────────────────────────────────────")
if errors:
    print(f"\n  {len(errors)} FAILURE(S):")
    for e in errors:
        print(f"    • {e}")
else:
    print("\n  All checks passed. Data is ready for Power BI refresh.")
print("=" * 65)
