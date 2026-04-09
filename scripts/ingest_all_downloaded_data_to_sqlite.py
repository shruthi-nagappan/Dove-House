#!/usr/bin/env python3
"""
Ingest raw project files under data_by_criteria/ (and ontology TTLs) into a single SQLite database.

What gets loaded as tables:
- CSV: loaded into tables (one table per file)
- XLSX/XLS: each sheet loaded into its own table
- JSON: stored as raw text + basic JSON validity flag
- TTL: parsed to triples (via rdflib) into a triples table
- HTML/TXT/MD: stored as raw text

What is indexed as files only (not unpacked):
- ZIP (e.g., shapefiles)
- PDF

Output:
  datawarehouse/dove_house_all_data.sqlite
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import rdflib

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "datawarehouse" / "dove_house_all_data.sqlite"


INCLUDE_DIRS = [
    ROOT / "data_by_criteria",
    ROOT / "IndianaHospitalDischarges" / "ontology",
]

INCLUDE_EXTS = {
    ".csv",
    ".xlsx",
    ".xls",
    ".json",
    ".ttl",
    ".html",
    ".htm",
    ".txt",
    ".md",
    ".zip",
    ".pdf",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    if not s:
        s = "table"
    if s[0].isdigit():
        s = "t_" + s
    return s


def table_name_for_file(path: Path) -> str:
    """Stable, unique SQLite table name (max 63 chars). Full path slug when short; else stem + path hash."""
    rel = str(path.relative_to(ROOT))
    full = slugify(rel)
    if len(full) <= 63:
        return full
    h = hashlib.sha256(rel.encode()).hexdigest()[:10]
    stem = slugify(path.stem)
    room = 63 - 11  # underscore + 10-char hex
    stem = stem[:room] if len(stem) > room else stem
    return f"{stem}_{h}"[:63]


def iter_dataset_files() -> list[Path]:
    files: list[Path] = []
    for d in INCLUDE_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() in INCLUDE_EXTS:
                files.append(p)
    # stable order
    return sorted(files, key=lambda p: str(p))


def ensure_core_tables(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS file_manifest (
          file_id INTEGER PRIMARY KEY AUTOINCREMENT,
          rel_path TEXT UNIQUE NOT NULL,
          abs_path TEXT NOT NULL,
          ext TEXT NOT NULL,
          bytes INTEGER NOT NULL,
          sha256 TEXT NOT NULL,
          ingested_at TEXT NOT NULL,
          status TEXT NOT NULL,
          notes TEXT
        );

        CREATE TABLE IF NOT EXISTS raw_text_files (
          rel_path TEXT PRIMARY KEY,
          content TEXT NOT NULL,
          FOREIGN KEY (rel_path) REFERENCES file_manifest(rel_path)
        );

        CREATE TABLE IF NOT EXISTS raw_json_files (
          rel_path TEXT PRIMARY KEY,
          content TEXT NOT NULL,
          is_valid_json INTEGER NOT NULL,
          FOREIGN KEY (rel_path) REFERENCES file_manifest(rel_path)
        );

        CREATE TABLE IF NOT EXISTS rdf_triples (
          rel_path TEXT NOT NULL,
          subject TEXT NOT NULL,
          predicate TEXT NOT NULL,
          object TEXT NOT NULL,
          object_is_literal INTEGER NOT NULL,
          PRIMARY KEY (rel_path, subject, predicate, object),
          FOREIGN KEY (rel_path) REFERENCES file_manifest(rel_path)
        );

        CREATE TABLE IF NOT EXISTS ingest_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          rel_path TEXT NOT NULL,
          event TEXT NOT NULL,
          detail TEXT,
          ts TEXT NOT NULL
        );
        """
    )


def log(con: sqlite3.Connection, rel_path: str, event: str, detail: str | None = None) -> None:
    con.execute(
        "INSERT INTO ingest_log(rel_path, event, detail, ts) VALUES (?,?,?,?)",
        (rel_path, event, detail, utc_now()),
    )


def upsert_manifest(con: sqlite3.Connection, path: Path, status: str, notes: str | None) -> str:
    rel = str(path.relative_to(ROOT))
    con.execute(
        """
        INSERT INTO file_manifest(rel_path, abs_path, ext, bytes, sha256, ingested_at, status, notes)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(rel_path) DO UPDATE SET
          abs_path=excluded.abs_path,
          ext=excluded.ext,
          bytes=excluded.bytes,
          sha256=excluded.sha256,
          ingested_at=excluded.ingested_at,
          status=excluded.status,
          notes=excluded.notes
        """,
        (
            rel,
            str(path),
            path.suffix.lower(),
            path.stat().st_size,
            sha256_file(path),
            utc_now(),
            status,
            notes,
        ),
    )
    return rel


def ingest_csv(con: sqlite3.Connection, path: Path, rel: str) -> None:
    tname = table_name_for_file(path)
    df = pd.read_csv(path)
    df.to_sql(tname, con, if_exists="replace", index=False)
    log(con, rel, "csv_loaded", f"table={tname} rows={len(df)} cols={len(df.columns)}")


def ingest_xlsx(con: sqlite3.Connection, path: Path, rel: str) -> None:
    xls = pd.ExcelFile(path)
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        combined = slugify(f"{table_name_for_file(path)}__{sheet}")
        if len(combined) <= 63:
            tname = combined
        else:
            h = hashlib.sha256(f"{rel}::{sheet}".encode()).hexdigest()[:10]
            tname = f"{slugify(path.stem)[:38]}_{slugify(sheet)[:8]}_{h}"[:63]
        df.to_sql(tname, con, if_exists="replace", index=False)
        log(con, rel, "xlsx_sheet_loaded", f"sheet={sheet} table={tname} rows={len(df)} cols={len(df.columns)}")


def ingest_text(con: sqlite3.Connection, path: Path, rel: str) -> None:
    content = path.read_text(encoding="utf-8", errors="replace")
    con.execute(
        """
        INSERT INTO raw_text_files(rel_path, content) VALUES (?,?)
        ON CONFLICT(rel_path) DO UPDATE SET content=excluded.content
        """,
        (rel, content),
    )
    log(con, rel, "text_stored", f"chars={len(content)}")


def ingest_json(con: sqlite3.Connection, path: Path, rel: str) -> None:
    content = path.read_text(encoding="utf-8", errors="replace")
    is_valid = 1
    try:
        json.loads(content)
    except Exception:
        is_valid = 0
    con.execute(
        """
        INSERT INTO raw_json_files(rel_path, content, is_valid_json) VALUES (?,?,?)
        ON CONFLICT(rel_path) DO UPDATE SET content=excluded.content, is_valid_json=excluded.is_valid_json
        """,
        (rel, content, is_valid),
    )
    log(con, rel, "json_stored", f"valid={is_valid} chars={len(content)}")


def ingest_ttl(con: sqlite3.Connection, path: Path, rel: str) -> None:
    g = rdflib.Graph()
    g.parse(str(path), format="turtle")
    con.execute("DELETE FROM rdf_triples WHERE rel_path = ?", (rel,))
    rows = []
    for s, p, o in g:
        rows.append((rel, str(s), str(p), str(o), 1 if isinstance(o, rdflib.Literal) else 0))
    con.executemany(
        """
        INSERT OR IGNORE INTO rdf_triples(rel_path, subject, predicate, object, object_is_literal)
        VALUES (?,?,?,?,?)
        """,
        rows,
    )
    log(con, rel, "ttl_parsed", f"triples={len(rows)}")


def ingest_all() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    files = iter_dataset_files()

    with sqlite3.connect(DB_PATH) as con:
        ensure_core_tables(con)

        for path in files:
            ext = path.suffix.lower()
            try:
                rel = upsert_manifest(con, path, status="seen", notes=None)
                if ext == ".csv":
                    ingest_csv(con, path, rel)
                    upsert_manifest(con, path, status="loaded_table", notes=None)
                elif ext in {".xlsx", ".xls"}:
                    ingest_xlsx(con, path, rel)
                    upsert_manifest(con, path, status="loaded_table", notes=None)
                elif ext in {".txt", ".md", ".html", ".htm"}:
                    ingest_text(con, path, rel)
                    upsert_manifest(con, path, status="stored_text", notes=None)
                elif ext == ".json":
                    ingest_json(con, path, rel)
                    upsert_manifest(con, path, status="stored_json", notes=None)
                elif ext == ".ttl":
                    ingest_ttl(con, path, rel)
                    upsert_manifest(con, path, status="parsed_rdf", notes=None)
                elif ext in {".zip", ".pdf"}:
                    # Keep as file reference only (manifest already has hash/size).
                    log(con, rel, "file_indexed", "binary_not_loaded")
                    upsert_manifest(con, path, status="indexed_only", notes="binary_not_loaded")
                else:
                    log(con, rel, "skipped", f"ext={ext}")
                    upsert_manifest(con, path, status="skipped", notes="unsupported_ext")
            except Exception as e:
                rel = str(path.relative_to(ROOT))
                log(con, rel, "error", repr(e))
                upsert_manifest(con, path, status="error", notes=repr(e))


if __name__ == "__main__":
    ingest_all()
    print(f"Built/updated: {DB_PATH}")

