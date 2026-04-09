#!/usr/bin/env python3
"""
Run the county overdose (CDC) + female population context (ACS) join against
datawarehouse/dove_house_all_data.sqlite.

Writes: datawarehouse/python_county_overdose_female_context.csv
"""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "datawarehouse" / "dove_house_all_data.sqlite"
OUT = ROOT / "datawarehouse" / "python_county_overdose_female_context.csv"

REL_CDC = Path(
    "data_by_criteria/04_substance_use_overdose/cdc/cdc_drug_poisoning_mortality_by_county_IN_pbkm_d27e.csv"
)
REL_ACS = Path(
    "data_by_criteria/01_economic_housing_stress/census_acs/acs_in_counties_population_female.csv"
)


_ingest_mod = None


def _ingest_table_name_for_file(path: Path) -> str:
    """Must match scripts/ingest_all_downloaded_data_to_sqlite.table_name_for_file."""
    global _ingest_mod
    if _ingest_mod is None:
        ingest_path = Path(__file__).resolve().parent / "ingest_all_downloaded_data_to_sqlite.py"
        spec = importlib.util.spec_from_file_location("ingest_all_downloaded_data", ingest_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load ingest module from {ingest_path}")
        _ingest_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ingest_mod)
    return _ingest_mod.table_name_for_file(path)


def pick_table(names: list[str], must_include: str) -> str:
    matches = [t for t in names if must_include in t]
    if not matches:
        raise RuntimeError(f"No table matching {must_include!r}. Available sample: {names[:20]}")
    if len(matches) > 1:
        # Prefer exact-ish: county IN pbkm
        for m in matches:
            if "pbkm" in m or "mortality_by_county" in m:
                return m
    return matches[0]


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Missing database: {DB}")

    con = sqlite3.connect(str(DB))

    tables = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]

    cdc_expected = _ingest_table_name_for_file(ROOT / REL_CDC)
    acs_expected = _ingest_table_name_for_file(ROOT / REL_ACS)
    cdc_tbl = cdc_expected if cdc_expected in tables else pick_table(tables, "cdc_drug_poisoning_mortality_by_county")
    acs_tbl = acs_expected if acs_expected in tables else pick_table(tables, "acs_in_counties_population_fema")

    print("Using tables:")
    print("  CDC:", cdc_tbl)
    print("  ACS:", acs_tbl)

    q = f"""
    WITH cdc AS (
      SELECT
        substr('00000' || fips, -5, 5) AS county_fips,
        CAST(year AS INTEGER) AS year,
        county,
        CAST(population AS INTEGER) AS cdc_population,
        estimated_age_adjusted_death_rate_11_categories_in_ranges AS rate_range
      FROM "{cdc_tbl}"
    ),
    acs AS (
      SELECT
        substr('00' || state, -2, 2) || substr('000' || county, -3, 3) AS county_fips,
        NAME AS county_name_acs,
        CAST(B01001_001E AS INTEGER) AS total_pop_acs,
        CAST(B01001_026E AS INTEGER) AS female_pop_acs
      FROM "{acs_tbl}"
    )
    SELECT
      c.county_fips,
      c.year,
      c.county,
      c.rate_range,
      c.cdc_population,
      a.county_name_acs,
      a.total_pop_acs,
      a.female_pop_acs,
      CASE
        WHEN a.total_pop_acs > 0 THEN 1.0 * a.female_pop_acs / a.total_pop_acs
      END AS female_share
    FROM cdc c
    LEFT JOIN acs a USING (county_fips)
    ORDER BY c.year DESC, c.county
    """

    df = pd.read_sql_query(q, con)
    con.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    print(f"Rows: {len(df):,}")
    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    main()
