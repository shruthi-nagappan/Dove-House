#!/usr/bin/env python3
"""
Honest v1 county database:
- CDC all-sex county drug poisoning mortality (rate ranges) for Indiana
- ACS female population denominator/context for Indiana counties

Outputs:
  datawarehouse/dove_house_honest_v1.sqlite
  datawarehouse/mart_county_overdose_context.csv
"""

from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "datawarehouse" / "dove_house_honest_v1.sqlite"
MART_CSV = ROOT / "datawarehouse" / "mart_county_overdose_context.csv"

CDC_IN_COUNTY = (
    ROOT
    / "data_by_criteria"
    / "04_substance_use_overdose"
    / "cdc"
    / "cdc_drug_poisoning_mortality_by_county_IN_pbkm_d27e.csv"
)
ACS_FEMALE = (
    ROOT
    / "data_by_criteria"
    / "01_economic_housing_stress"
    / "census_acs"
    / "acs_in_counties_population_female.csv"
)


def parse_rate_midpoint(s: str | None) -> float | None:
    """
    CDC file encodes age-adjusted death rate as a category/range string like:
      '6.1-8', '18.1-20', '50+' or sometimes missing.
    We convert ranges to midpoints; for 'X+' use X as a conservative lower-bound proxy.
    """
    if not s:
        return None
    s = s.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", s)
    if m:
        a = float(m.group(1))
        b = float(m.group(2))
        return (a + b) / 2.0
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*\+", s)
    if m:
        return float(m.group(1))
    return None


@dataclass(frozen=True)
class CountyKey:
    county_fips: str  # 5-digit
    county_name: str


def load_acs_female(path: Path) -> dict[str, dict]:
    """
    ACS columns:
      NAME, B01001_001E (total), B01001_026E (female total), state, county
    county_fips = state(2) + county(3)
    """
    out: dict[str, dict] = {}
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            state = row["state"].zfill(2)
            county = row["county"].zfill(3)
            fips = state + county
            out[fips] = {
                "county_name": row["NAME"],
                "acs_total_pop": int(float(row["B01001_001E"])) if row["B01001_001E"] else None,
                "acs_female_pop": int(float(row["B01001_026E"])) if row["B01001_026E"] else None,
            }
    return out


def load_cdc_county(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            fips = (row.get("fips") or "").strip().zfill(5)
            year = int(row["year"])
            pop = int(float(row["population"])) if row.get("population") else None
            rate_range = (row.get("estimated_age_adjusted_death_rate_11_categories_in_ranges") or "").strip()
            out.append(
                {
                    "county_fips": fips,
                    "year": year,
                    "county_label": row.get("county"),
                    "population": pop,
                    "rate_range": rate_range or None,
                    "rate_midpoint": parse_rate_midpoint(rate_range),
                }
            )
    return out


def build_db() -> None:
    if not CDC_IN_COUNTY.exists():
        raise FileNotFoundError(f"Missing CDC file: {CDC_IN_COUNTY}")
    if not ACS_FEMALE.exists():
        raise FileNotFoundError(f"Missing ACS female file: {ACS_FEMALE}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    acs = load_acs_female(ACS_FEMALE)
    cdc = load_cdc_county(CDC_IN_COUNTY)

    # Build county dimension from ACS as canonical list.
    dim_county = []
    for fips, a in sorted(acs.items()):
        dim_county.append((fips, a["county_name"], "IN"))

    with sqlite3.connect(DB_PATH) as con:
        con.execute("PRAGMA foreign_keys = ON;")

        con.executescript(
            """
            DROP TABLE IF EXISTS fact_cdc_drug_poisoning_mortality_county;
            DROP TABLE IF EXISTS fact_acs_county_population;
            DROP TABLE IF EXISTS dim_county;

            CREATE TABLE dim_county (
              county_fips TEXT PRIMARY KEY,
              county_name TEXT NOT NULL,
              state TEXT NOT NULL
            );

            CREATE TABLE fact_acs_county_population (
              county_fips TEXT NOT NULL,
              year INTEGER NOT NULL,
              total_pop INTEGER,
              female_pop INTEGER,
              female_share REAL,
              PRIMARY KEY (county_fips, year),
              FOREIGN KEY (county_fips) REFERENCES dim_county(county_fips)
            );

            CREATE TABLE fact_cdc_drug_poisoning_mortality_county (
              county_fips TEXT NOT NULL,
              year INTEGER NOT NULL,
              population INTEGER,
              rate_range TEXT,
              rate_midpoint REAL,
              PRIMARY KEY (county_fips, year),
              FOREIGN KEY (county_fips) REFERENCES dim_county(county_fips)
            );
            """
        )

        con.executemany(
            "INSERT INTO dim_county(county_fips, county_name, state) VALUES (?,?,?)",
            dim_county,
        )

        # ACS is a single year (ACS 2023 5-year). Store it as year=2023 for join purposes.
        acs_year = 2023
        acs_rows = []
        for fips, a in acs.items():
            total_pop = a["acs_total_pop"]
            female_pop = a["acs_female_pop"]
            female_share = (female_pop / total_pop) if (female_pop and total_pop) else None
            acs_rows.append((fips, acs_year, total_pop, female_pop, female_share))
        con.executemany(
            """
            INSERT INTO fact_acs_county_population(county_fips, year, total_pop, female_pop, female_share)
            VALUES (?,?,?,?,?)
            """,
            acs_rows,
        )

        cdc_rows = [
            (r["county_fips"], r["year"], r["population"], r["rate_range"], r["rate_midpoint"])
            for r in cdc
            if r["county_fips"] in acs
        ]
        con.executemany(
            """
            INSERT INTO fact_cdc_drug_poisoning_mortality_county(county_fips, year, population, rate_range, rate_midpoint)
            VALUES (?,?,?,?,?)
            """,
            cdc_rows,
        )

        # Build mart as a query and export to CSV
        q = """
        SELECT
          c.county_fips,
          d.county_name,
          m.year AS cdc_year,
          m.population AS cdc_population,
          m.rate_range,
          m.rate_midpoint,
          a.year AS acs_year,
          a.total_pop AS acs_total_pop,
          a.female_pop AS acs_female_pop,
          a.female_share
        FROM fact_cdc_drug_poisoning_mortality_county m
        JOIN dim_county d ON d.county_fips = m.county_fips
        LEFT JOIN fact_acs_county_population a
          ON a.county_fips = m.county_fips AND a.year = 2023
        JOIN dim_county c ON c.county_fips = m.county_fips
        ORDER BY m.year DESC, d.county_name ASC
        """
        rows = con.execute(q).fetchall()
        cols = [c[0] for c in con.execute(q).description]

    MART_CSV.parent.mkdir(parents=True, exist_ok=True)
    with MART_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)


if __name__ == "__main__":
    build_db()
    print(f"Built: {DB_PATH}")
    print(f"Wrote: {MART_CSV}")

