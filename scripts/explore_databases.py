#!/usr/bin/env python3
"""
Explore and summarize Dove House SQLite databases so you can understand what is inside.

Usage:
  python3 scripts/explore_databases.py
  python3 scripts/explore_databases.py --db all_data
  python3 scripts/explore_databases.py --db honest_v1
  python3 scripts/explore_databases.py --output datawarehouse/database_overview.txt

Defaults: summarizes both databases under datawarehouse/
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parents[1]
DB_ALL = ROOT / "datawarehouse" / "dove_house_all_data.sqlite"
DB_HONEST = ROOT / "datawarehouse" / "dove_house_honest_v1.sqlite"


def fmt(n: int) -> str:
    return f"{n:,}"


def table_row_count(con: sqlite3.Connection, name: str) -> int | None:
    try:
        return con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
    except sqlite3.Error:
        return None


def summarize_db(path: Path, out: TextIO, max_sample_tables: int = 8) -> None:
    if not path.exists():
        print(f"\n[SKIP] Not found: {path}", file=out)
        return

    size_mb = path.stat().st_size / 1_048_576
    con = sqlite3.connect(str(path))
    tables = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]

    print(f"\n{'=' * 72}", file=out)
    print(f"DATABASE: {path.name}", file=out)
    print(f"Path: {path}", file=out)
    print(f"Size: ~{size_mb:.2f} MiB", file=out)
    print(f"Tables: {len(tables)}", file=out)
    print(f"{'=' * 72}", file=out)

    # Row counts for every table (compact)
    rows_info: list[tuple[str, int | None]] = []
    for t in tables:
        rows_info.append((t, table_row_count(con, t)))
    rows_info.sort(key=lambda x: (x[1] is None, -(x[1] or 0)))

    print("\n-- Tables by approximate size (largest first) --", file=out)
    for name, n in rows_info[:40]:
        r = "?" if n is None else fmt(n)
        print(f"  {r:>12}  {name}", file=out)
    if len(rows_info) > 40:
        print(f"  ... {len(rows_info) - 40} more tables", file=out)

    # Column detail for a few important / large tables
    print("\n-- Column schemas (sample of tables) --", file=out)
    for name, n in rows_info[:max_sample_tables]:
        if n is None:
            continue
        print(f"\n[{name}]  ~{fmt(n)} rows", file=out)
        cols = con.execute(f'PRAGMA table_info("{name}")').fetchall()
        for cid, cname, ctype, notnull, dflt, pk in cols:
            pk_s = " PK" if pk else ""
            print(f"    {cname}: {ctype or 'ANY'}{pk_s}", file=out)

    # Special: honest_v1 star schema reminder
    if path.name == "dove_house_honest_v1.sqlite":
        print("\n-- Model note (Honest v1) --", file=out)
        print(
            "  dim_county + fact_acs_county_population + fact_cdc_drug_poisoning_mortality_county",
            file=out,
        )
        print("  Mart CSV (flat join): datawarehouse/mart_county_overdose_context.csv", file=out)

    # Special: all_data manifest
    if path.name == "dove_house_all_data.sqlite" and "file_manifest" in tables:
        print("\n-- file_manifest summary --", file=out)
        st = con.execute(
            "SELECT status, COUNT(*) FROM file_manifest GROUP BY status ORDER BY COUNT(*) DESC"
        ).fetchall()
        for status, c in st:
            print(f"  {fmt(c):>6}  {status}", file=out)
        print("\n-- Recent ingest_log (last 15) --", file=out)
        logs = con.execute(
            "SELECT ts, rel_path, event, detail FROM ingest_log ORDER BY id DESC LIMIT 15"
        ).fetchall()
        for ts, rel, ev, det in logs:
            det_s = (det or "")[:80]
            print(f"  {ts} | {ev:16} | {rel[:50]}", file=out)
            if det_s:
                print(f"      {det_s}", file=out)

    con.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Summarize Dove House SQLite databases.")
    p.add_argument(
        "--db",
        choices=("all", "all_data", "honest_v1"),
        default="all",
        help="Which database to summarize (default: both)",
    )
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write report to this file as well as stdout",
    )
    p.add_argument(
        "--sample-tables",
        type=int,
        default=8,
        help="How many largest tables get full column listings",
    )
    args = p.parse_args()

    targets: list[Path] = []
    if args.db in ("all", "all_data"):
        targets.append(DB_ALL)
    if args.db in ("all", "honest_v1"):
        targets.append(DB_HONEST)

    streams: list[TextIO] = [sys.stdout]
    fobj: TextIO | None = None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fobj = args.output.open("w", encoding="utf-8")
        streams.append(fobj)

    try:
        for stream in streams:
            print("Dove House — SQLite database overview", file=stream)
            print("(Run from project root: python3 scripts/explore_databases.py)", file=stream)
            for db_path in targets:
                summarize_db(db_path, stream, max_sample_tables=args.sample_tables)
            print("\nDone.", file=stream)
    finally:
        if fobj is not None:
            fobj.close()
            print(f"Wrote: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
